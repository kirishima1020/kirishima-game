"""模倣の質を直接測る：policy top-1 一致率（argmax==教師手）と 価値の符号一致率。
  top-1が高いのに弱い → MCTS/playのbug。top-1が低い → 模倣不足（学習/目標の問題）。
使い方: python diag2.py [ckpt/net_warm.pt] [N=7] [games=30]
"""
import sys, json, torch
import engine as E, model as MD

ckpt = sys.argv[1] if len(sys.argv) > 1 else 'ckpt/net_warm.pt'
N = int(sys.argv[2]) if len(sys.argv) > 2 else 7
NG = int(sys.argv[3]) if len(sys.argv) > 3 else 30

net = MD.Net(N); net.load_state_dict(torch.load(ckpt, map_location='cpu')); net.eval()
rows = [json.loads(l) for l in open('teacher.ndjson') if l.strip()][:NG]

c = t = vc = vt = 0
for g in rows:
    if g.get('N') != N: continue
    s = E.make_game(N, 2); w = g['winner']
    for mid in g['ids']:
        mover = s.turn
        x = torch.from_numpy(E.planes(s)).unsqueeze(0)
        with torch.no_grad():
            logits, v = net(x)
        lm = E.legal_moves(s, mover)
        best = max(lm, key=lambda m: float(logits[0, m]))
        c += int(best == mid); t += 1
        actual = 1 if w == mover else (-1 if w != 0 else 0)
        if actual != 0:
            vc += int((float(v[0]) > 0) == (actual > 0)); vt += 1
        E.play(s, mid, mover)

print(f'ckpt={ckpt}  positions={t}')
print(f'policy top-1 一致率 = {c/t:.2f}  (argmax が教師の手と一致／模倣の質)')
print(f'value 符号一致率   = {vc/max(1,vt):.2f}  (価値の向きが勝敗と合う率)')
