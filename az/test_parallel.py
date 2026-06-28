"""並列自己対局プラミングのローカル検証（torch不要・スタブ評価器）。
fork で各ワーカが親の _EVAL を継承し、複数コアからサンプルが返るかを見る。"""
import multiprocessing as mp
mp.set_start_method('fork', force=True)
import time, random, engine as E, train as T


def stub(s):
    lm = E.legal_moves(s, s.turn)
    p = {m: 1.0 / len(lm) for m in lm} if lm else {}
    me = s.turn; opp = 2 if me == 1 else 1
    v = (s.score[me] - s.score[opp]) / (s.M * s.M)
    return p, max(-1.0, min(1.0, v))


T._EVAL = stub; T._N = 7; T._SIMS = 24

for W in (1, 4):
    t0 = time.time()
    samples = T.parallel_selfplay(games_per_worker=2, workers=W, base_seed=42)
    dt = time.time() - t0
    pl, pol, v = samples[0]
    print(f'workers={W} games={W*2} -> samples={len(samples)}  {dt:.1f}s  '
          f'(sample: planes{pl.shape} polΣ={float(pol.sum()):.2f} v={v:+.2f})')
