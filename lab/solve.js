'use strict';
// キリシマ 2人厳密ソルバ（終盤読み切り）。
// margin = score[1]-score[2] を、手番1が最大化・手番2が最小化する alpha-beta min-max。
// 完全情報・運なしなので、返す margin と手は「双方最善のときの厳密な答え」。
// 使い方:    node solve.js            （自己検証）
//   API:     const {solve}=require('./solve'); solve(state) -> {margin,move,nodes,ms}
const E = require('../engine');
const { EC, HC, clone, play, legal } = E;

// 候補手を置いたら何マス閉じるか（置く→数える→戻す。engine.captureGain 相当を内製）。
function gainOf(s, id) {
  const hc = HC(s.N); let isH, ei;
  if (id < hc) { isH = true; ei = id; } else { isH = false; ei = id - hc; }
  if (isH) s.H[ei] = 1; else s.V[ei] = 1;
  let g = countEnclosed(s);
  if (isH) s.H[ei] = 0; else s.V[ei] = 0;
  return g;
}
// 未塗り かつ 外部非連結のセル数（engine.fill の数えるだけ版）。
function countEnclosed(s) {
  const M = s.M, N = s.N, H = s.H, V = s.V, c = s.cells;
  const conn = new Uint8Array(M * M), q = new Int32Array(M * M);
  let qt = 0, qh = 0;
  for (let y = 0; y < M; y++) for (let x = 0; x < M; x++) {
    if (x !== 0 && x !== M - 1 && y !== 0 && y !== M - 1) continue;
    let o = false;
    if (x === 0 && V[y * N] === 0) o = true;
    else if (x === M - 1 && V[y * N + x + 1] === 0) o = true;
    else if (y === 0 && H[x] === 0) o = true;
    else if (y === M - 1 && H[(y + 1) * (N - 1) + x] === 0) o = true;
    if (o && !conn[y * M + x]) { conn[y * M + x] = 1; q[qt++] = y * M + x; }
  }
  while (qh < qt) {
    const cc = q[qh++], cx = cc % M, cy = (cc / M) | 0;
    if (cx + 1 < M && !conn[cy * M + cx + 1] && V[cy * N + cx + 1] === 0) { conn[cy * M + cx + 1] = 1; q[qt++] = cy * M + cx + 1; }
    if (cx - 1 >= 0 && !conn[cy * M + cx - 1] && V[cy * N + cx] === 0) { conn[cy * M + cx - 1] = 1; q[qt++] = cy * M + cx - 1; }
    if (cy + 1 < M && !conn[(cy + 1) * M + cx] && H[(cy + 1) * (N - 1) + cx] === 0) { conn[(cy + 1) * M + cx] = 1; q[qt++] = (cy + 1) * M + cx; }
    if (cy - 1 >= 0 && !conn[(cy - 1) * M + cx] && H[cy * (N - 1) + cx] === 0) { conn[(cy - 1) * M + cx] = 1; q[qt++] = (cy - 1) * M + cx; }
  }
  let g = 0; for (let i = 0; i < M * M; i++) if (c[i] === 0 && !conn[i]) g++;
  return g;
}

// 深さごとの手バッファ（共有 engine バッファの clobber 回避）。
let _bufs = [];
let _nodes = 0;

// s から双方最善のときの margin を返す。pruning あり。
function ab(s, depth, alpha, beta) {
  _nodes++;
  if (s.turn === 0) return s.score[1] - s.score[2];
  const ec = EC(s.N);
  let lb = _bufs[depth]; if (!lb || lb.length < ec) lb = _bufs[depth] = new Int32Array(ec);
  const n = legal(s, s.turn, lb);
  if (n === 0) { const ns = clone(s); E.advance(ns); return ns.turn === s.turn ? s.score[1] - s.score[2] : ab(ns, depth + 1, alpha, beta); }
  // 手順付け：捕獲ゲイン降順（枝刈りを効かせる）。
  const ids = new Array(n), gns = new Array(n);
  for (let i = 0; i < n; i++) { ids[i] = lb[i]; gns[i] = gainOf(s, lb[i]); }
  for (let i = 1; i < n; i++) { const id = ids[i], g = gns[i]; let j = i - 1; while (j >= 0 && gns[j] < g) { ids[j + 1] = ids[j]; gns[j + 1] = gns[j]; j--; } ids[j + 1] = id; gns[j + 1] = g; }
  const maxing = (s.turn === 1);
  let best = maxing ? -Infinity : Infinity;
  for (let i = 0; i < n; i++) {
    const ns = clone(s); play(ns, ids[i], s.turn);
    const v = ab(ns, depth + 1, alpha, beta);
    if (maxing) { if (v > best) best = v; if (best > alpha) alpha = best; }
    else { if (v < best) best = v; if (best < beta) beta = best; }
    if (alpha >= beta) break;
  }
  return best;
}

// 根：厳密 margin と最善手を返す。
function solve(state) {
  if (state.P !== 2) throw new Error('solve は2人戦のみ（P=2）');
  _nodes = 0; const t0 = process.hrtime.bigint();
  const s = clone(state);
  if (s.turn === 0) return { margin: s.score[1] - s.score[2], move: -1, nodes: 1, ms: 0 };
  const ec = EC(s.N), lb = new Int32Array(ec), n = legal(s, s.turn, lb);
  const ids = new Array(n), gns = new Array(n);
  for (let i = 0; i < n; i++) { ids[i] = lb[i]; gns[i] = gainOf(s, lb[i]); }
  for (let i = 1; i < n; i++) { const id = ids[i], g = gns[i]; let j = i - 1; while (j >= 0 && gns[j] < g) { ids[j + 1] = ids[j]; gns[j + 1] = gns[j]; j--; } ids[j + 1] = id; gns[j + 1] = g; }
  const maxing = (s.turn === 1);
  let best = maxing ? -Infinity : Infinity, bestMove = ids[0], alpha = -Infinity, beta = Infinity;
  for (let i = 0; i < n; i++) {
    const ns = clone(s); play(ns, ids[i], s.turn);
    const v = ab(ns, 1, alpha, beta);
    if (maxing) { if (v > best) { best = v; bestMove = ids[i]; } if (best > alpha) alpha = best; }
    else { if (v < best) { best = v; bestMove = ids[i]; } if (best < beta) beta = best; }
  }
  const ms = Number(process.hrtime.bigint() - t0) / 1e6;
  return { margin: best, move: bestMove, nodes: _nodes, ms };
}

// 主手順（PV）：根から最善手を辿って終局まで。検証用。
function principalVariation(state) {
  let s = clone(state); const line = [];
  while (s.turn !== 0) { const r = solve(s); if (r.move < 0) break; line.push({ turn: s.turn, move: r.move, margin: r.margin }); play(s, r.move, s.turn); }
  return { line, final: s.score[1] - s.score[2], score: [s.score[1], s.score[2]] };
}

// 空きセルを「開いた共有辺でつながった連結成分」に分ける（分解の素）。
// 二つの空きセルは、間の辺が未引き(0)なら同じ成分。＝territory と同じ隣接。
// 返り値: { comps:[{cells:[idx...],size}], compOf:Int32Array(M*M)（空きでないセルは-1） }
function components(s) {
  const M = s.M, N = s.N, H = s.H, V = s.V, c = s.cells;
  const compOf = new Int32Array(M * M).fill(-1);
  const comps = []; const q = [];
  for (let start = 0; start < M * M; start++) {
    if (c[start] !== 0 || compOf[start] >= 0) continue;
    const id = comps.length; const cells = [];
    compOf[start] = id; q.length = 0; q.push(start);
    while (q.length) {
      const cc = q.pop(), cx = cc % M, cy = (cc / M) | 0; cells.push(cc);
      if (cx + 1 < M && V[cy * N + cx + 1] === 0) { const nb = cy * M + cx + 1; if (c[nb] === 0 && compOf[nb] < 0) { compOf[nb] = id; q.push(nb); } }
      if (cx - 1 >= 0 && V[cy * N + cx] === 0) { const nb = cy * M + cx - 1; if (c[nb] === 0 && compOf[nb] < 0) { compOf[nb] = id; q.push(nb); } }
      if (cy + 1 < M && H[(cy + 1) * (N - 1) + cx] === 0) { const nb = (cy + 1) * M + cx; if (c[nb] === 0 && compOf[nb] < 0) { compOf[nb] = id; q.push(nb); } }
      if (cy - 1 >= 0 && H[cy * (N - 1) + cx] === 0) { const nb = (cy - 1) * M + cx; if (c[nb] === 0 && compOf[nb] < 0) { compOf[nb] = id; q.push(nb); } }
    }
    comps.push({ cells, size: cells.length });
  }
  return { comps, compOf };
}

// ---- 置換表つき「丸ごと解き」（strongly solve）----
// 鍵：盤面（H,V,cells,first,turn）だけ。将来 margin（=これ以降の score差の変化）は
// 現在スコアに依らず盤面だけで決まるので、手順違いの同一局面を共有できる。
// このゲームは辺が可換で同一局面への到達経路が膨大なため、置換表が指数を潰す。
// maxNodes を超えたら BudgetError を投げる（呼び出し側が退避できるよう）。
class BudgetError extends Error {}
function solveStrong(state, maxNodes = Infinity) {
  if (state.P !== 2) throw new Error('2人戦のみ');
  const TT = new Map(); let nodes = 0;
  const ec = EC(state.N);
  function key(s) { return s.turn + ':' + s.H.join('') + ':' + s.V.join('') + ':' + s.cells.join('') + ':' + s.first.join(''); }
  // s からの「将来 margin」（双方最善）。
  function fut(s) {
    if (s.turn === 0) return 0;
    const k = key(s); const hit = TT.get(k); if (hit !== undefined) return hit;
    if (++nodes > maxNodes) throw new BudgetError('budget');
    const lb = new Int32Array(ec), n = legal(s, s.turn, lb);
    if (n === 0) { const ns = clone(s); E.advance(ns); const v = ns.turn === s.turn ? 0 : fut(ns); TT.set(k, v); return v; }
    const base = s.score[1] - s.score[2], maxing = s.turn === 1;
    let best = maxing ? -Infinity : Infinity;
    for (let i = 0; i < n; i++) { const ns = clone(s); play(ns, lb[i], s.turn); const v = (ns.score[1] - ns.score[2] - base) + fut(ns); if (maxing ? v > best : v < best) best = v; }
    TT.set(k, best); return best;
  }
  const t0 = process.hrtime.bigint();
  const s = clone(state);
  const lb = new Int32Array(ec), n = legal(s, s.turn, lb);
  const base = s.score[1] - s.score[2], maxing = s.turn === 1;
  let best = maxing ? -Infinity : Infinity, move = -1;
  for (let i = 0; i < n; i++) { const ns = clone(s); play(ns, lb[i], s.turn); const v = (ns.score[1] - ns.score[2] - base) + fut(ns); if (move < 0 || (maxing ? v > best : v < best)) { best = v; move = lb[i]; } }
  const ms = Number(process.hrtime.bigint() - t0) / 1e6;
  return { margin: base + best, move, nodes, ttSize: TT.size, ms };
}

// 終盤係：2人戦で空きセルが少なければ厳密手を返す。重ければ（予算超過）null を返し、
// 呼び出し側はロールアウト等に退避する。＝AIの「終盤に入ったらソルバへ切替」分岐。
function solverMove(state, { maxCells = 11, maxNodes = 5_000_000 } = {}) {
  if (state.P !== 2 || state.turn === 0) return null;
  let empty = 0; for (let i = 0; i < state.cells.length; i++) if (state.cells[i] === 0) empty++;
  if (empty > maxCells) return null;
  try { return solveStrong(state, maxNodes); }
  catch (e) { if (e instanceof BudgetError) return null; throw e; }
}

// 領域分解ソルバは不採用。区画を独立部分ゲームとして別々に解いて合算する手法を試したが、
// solveStrong との総当たり照合で約3%の局面が食い違った（例: N=4 真margin=9 を 7 と誤判定）。
// 原因＝自網リーチ規則が壁で分かれた区画を「共有頂点」で溶接し、区画が独立しないため。
// ＝ドッツ式のパリティ分解はこのゲームには成立しない。components() は構造測定用に残す。

module.exports = { solve, solveStrong, solverMove, components, principalVariation, countEnclosed, gainOf };

// ---- 自己検証 ----
if (require.main === module) {
  const { makeGame } = E;
  console.log('=== 検証1: 全幅 vs alpha-beta が一致するか（N=3 空盤から） ===');
  // pruning なしの参照実装
  function full(s) {
    if (s.turn === 0) return s.score[1] - s.score[2];
    const ec = EC(s.N), lb = new Int32Array(ec), n = legal(s, s.turn, lb);
    if (n === 0) { const ns = clone(s); E.advance(ns); return ns.turn === s.turn ? s.score[1] - s.score[2] : full(ns); }
    const vals = [];
    for (let i = 0; i < n; i++) { const ns = clone(s); play(ns, lb[i], s.turn); vals.push(full(ns)); }
    return s.turn === 1 ? Math.max(...vals) : Math.min(...vals);
  }
  let g = makeGame(3, 2);
  const ref = full(clone(g));
  const r = solve(g);
  console.log(`  全幅 margin=${ref}  /  alpha-beta margin=${r.margin}  nodes=${r.nodes}  ${r.ms.toFixed(1)}ms  → ${ref === r.margin ? 'OK' : '不一致!!'}`);

  console.log('=== 検証2: PV を実エンジンで再生して最終 margin が一致するか ===');
  const pv = principalVariation(g);
  console.log(`  根 margin=${r.margin}  /  PV再生 final=${pv.final}  score=[${pv.score}]  手数=${pv.line.length}  → ${r.margin === pv.final ? 'OK' : '不一致!!'}`);

  console.log('=== 検証3: 終盤からどこまで厳密に読み切れるか（実際の使い方） ===');
  // 2人戦を rollout AI で終局まで打ち、各局面を記録 → 終局側から1手ずつ遡って厳密解。
  // 「残り合法手」が増えると指数で重くなる。どこまで実用かを測る。
  for (const N of [5, 6]) {
    E.setSeed(7);
    let s = makeGame(N, 2); const states = [clone(s)];
    while (s.turn !== 0) { const m = E.best(s, 300, true, false); if (m < 0) break; play(s, m, s.turn); states.push(clone(s)); }
    const L = states.length - 1;
    console.log(`  --- N=${N}（${N - 1}×${N - 1}=${(N - 1) * (N - 1)}マス） 対局長 ${L}手 ---`);
    console.log(`     終局からの距離  根の合法手  margin   nodes      時間`);
    const ec = EC(N), lb = new Int32Array(ec);
    let prevOk = true;
    for (let back = 1; back <= L && prevOk; back++) {
      const st = states[L - back];
      if (st.turn === 0) continue;
      const nLegal = legal(st, st.turn, lb);
      const r = solve(st);
      // PV 再生で厳密性を二重確認
      const pvr = principalVariation(st);
      const ok = r.margin === pvr.final;
      console.log(`        ${String(back).padStart(3)}手         ${String(nLegal).padStart(4)}     ${String(r.margin).padStart(4)}   ${String(r.nodes).padStart(9)}  ${r.ms.toFixed(1).padStart(8)}ms ${ok ? '' : ' ← 不一致!!'}`);
      if (r.ms > 3000) { console.log(`        （3秒超え：この深さが実用上限。ここで打ち切り）`); break; }
    }
  }
}
