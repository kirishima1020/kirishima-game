'use strict';
// キリシマ 3人厳密ソルバ（maxⁿ）＋キングメーカー検査。
// 各ノードで手番 p は「自分の最終得点」を最大化する。返り値は最終得点ベクトル [s1,s2,s3]。
// 同点（自分の得点が同じ手が複数）のときは手id最小で決める（決定的にするための便宜的規約）。
//
// キングメーカー局面の定義（古典的な病理）：
//   手番 p の合法手すべてが p 自身の最終得点を同じにする（p は自分の結果を変えられない）。
//   かつ、その手によって「勝者」が変わる（p が他者の勝敗だけを決める）。
// 桐島の仮説：自網延伸で最下位も常に自得点を増やせる→ p が完全に無差別な局面は出ない。
// これを N=3 を全解して数で検証する。
//
// 使い方: node solve3.js [N=3]
const E = require('../engine');
const { EC, clone, play, legal } = E;

function winnersOf(v) {            // 最大得点者の集合（同点は複数）。1..3 の Set。
  const mx = Math.max(v[0], v[1], v[2]);
  const s = new Set();
  for (let i = 0; i < 3; i++) if (v[i] === mx) s.add(i + 1);
  return s;
}
function sameSet(a, b) { if (a.size !== b.size) return false; for (const x of a) if (!b.has(x)) return false; return true; }

function solve3(N) {
  const TT = new Map();
  let nodes = 0, indifferent = 0, kingmaker = 0;
  const ec = EC(N);

  function key(s) { return s.turn + ':' + s.H.join('') + ':' + s.V.join('') + ':' + s.cells.join('') + ':' + s.first.join(''); }

  function val(s) {
    if (s.turn === 0) return [s.score[1], s.score[2], s.score[3]];
    const k = key(s); const hit = TT.get(k); if (hit) return hit;
    nodes++;
    const lb = new Int32Array(ec), n = legal(s, s.turn, lb);
    if (n === 0) { const ns = clone(s); E.advance(ns); const v = ns.turn === s.turn ? [s.score[1], s.score[2], s.score[3]] : val(ns); TT.set(k, v); return v; }
    const p = s.turn;
    const ids = [], vecs = [];
    for (let i = 0; i < n; i++) { const ns = clone(s); play(ns, lb[i], p); ids.push(lb[i]); vecs.push(val(ns)); }
    // p 自身の得点 vec[p-1] の最大
    let mx = -Infinity, mn = Infinity;
    for (const v of vecs) { const o = v[p - 1]; if (o > mx) mx = o; if (o < mn) mn = o; }
    // キングメーカー検査：p の全合法手が自得点同じ（mx==mn）＝ p は自分の結果を変えられない
    if (mx === mn) {
      indifferent++;
      // その手で勝者集合が変わるか
      const w0 = winnersOf(vecs[0]);
      let differs = false;
      for (let i = 1; i < vecs.length; i++) if (!sameSet(winnersOf(vecs[i]), w0)) { differs = true; break; }
      if (differs) kingmaker++;
    }
    // 値：自得点最大の手のうち、手id最小を採用（決定的）
    let best = null, bestId = Infinity;
    for (let i = 0; i < n; i++) if (vecs[i][p - 1] === mx && ids[i] < bestId) { bestId = ids[i]; best = vecs[i]; }
    TT.set(k, best); return best;
  }

  const t0 = process.hrtime.bigint();
  const root = E.makeGame(N, 3);
  const v = val(root);
  const ms = Number(process.hrtime.bigint() - t0) / 1e6;
  return { value: v, nodes, unique: TT.size, indifferent, kingmaker, ms };
}

if (require.main === module) {
  const N = process.argv[2] ? parseInt(process.argv[2]) : 3;
  console.log(`3人 maxⁿ 全解 N=${N}（盤 ${N - 1}×${N - 1}=${(N - 1) * (N - 1)}マス）…`);
  const r = solve3(N);
  console.log(`初手番(P1)から最善で進めた最終得点ベクトル: [${r.value}]`);
  console.log(`調べた局面 unique=${r.unique}  ${r.ms.toFixed(0)}ms`);
  console.log(`無差別局面（手番が自得点を一切変えられない）: ${r.indifferent}`);
  console.log(`キングメーカー局面（無差別かつ勝者が変わる）  : ${r.kingmaker}`);
  console.log(r.kingmaker === 0
    ? '→ キングメーカー局面ゼロ。桐島の仮説（着手制約で解消）をこの盤で支持。'
    : `→ キングメーカー局面が ${r.kingmaker} 件。仮説はこの盤では成立しない。要検討。`);
}

module.exports = { solve3 };
