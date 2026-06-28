'use strict';
// ver2+（捕獲認識ロールアウトMCTS・勝敗目標）の自己対局を回し、教師データを吐く。
// 各局: 手id列＋勝者。Python(engine.py)で再生して behavior cloning（ウォームスタート）。
// 使い方: node az_teacher.js [N=7] [iters=400] [games=120] > teacher.ndjson  2> teacher.log
const { setSeed, makeGame, ensure, best, play } = require('../engine');

const N = +process.argv[2] || 7, IT = +process.argv[3] || 400, G = +process.argv[4] || 120;
const out = [];
for (let g = 0; g < G; g++) {
  setSeed(1000 + g * 7); ensure(N);
  const s = makeGame(N, 2), ids = [], cap = (N - 1) * (N - 1) * 4 + 60;
  while (s.turn !== 0) { const mv = best(s, IT, true, false); ids.push(mv); play(s, mv, s.turn); if (s.moves > cap) break; }
  const winner = s.score[1] > s.score[2] ? 1 : (s.score[2] > s.score[1] ? 2 : 0);
  out.push(JSON.stringify({ N, ids, winner, score: [s.score[1], s.score[2]] }));
  if ((g + 1) % 10 === 0) process.stderr.write(`teacher ${g + 1}/${G}\n`);
}
process.stdout.write(out.join('\n') + '\n');
