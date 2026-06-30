"""学習網の弱さ診断。チェックポイントを「貪欲」(物差し) に当て、どこが壊れてるか切り分ける。
  生policy(探索なし) と 網-MCTS sims=50/200/800 の勝率を出す。
  - policyは貪欲に勝つのにMCTSが負ける → 価値かMCTSのバグ。
  - policyも負ける → 模倣が打ち筋に化けてない（符号化/policyの問題）。
  - simsを上げて改善 → ただの探索不足。
使い方: python diag.py [ckpt/net_latest.pt] [N=7]
"""
import sys, random
import torch
import engine as E, mcts as MC, baseline as BL, model as MD

ckpt = sys.argv[1] if len(sys.argv) > 1 else 'ckpt/net_latest.pt'
N = int(sys.argv[2]) if len(sys.argv) > 2 else 7
G = int(sys.argv[3]) if len(sys.argv) > 3 else 20
SIMS = [int(x) for x in sys.argv[4].split(',')] if len(sys.argv) > 4 else [50, 200, 800]
device = 'cuda' if torch.cuda.is_available() else 'cpu'

net = MD.Net(N).to(device)
net.load_state_dict(torch.load(ckpt, map_location=device)); net.eval()
ev = MD.make_evaluator(net, device)
rng = random.Random(7)
cap = (N - 1) * (N - 1) * 4 + 60


def vs_greedy(mover_fn):
    w = 0
    for g in range(G):
        seat = (g % 2) + 1; s = E.make_game(N, 2)
        while s.turn != 0:
            mv = mover_fn(s) if s.turn == seat else BL.greedy_move(s, rng)
            if mv < 0: break
            E.play(s, mv, s.turn)
            if s.moves > cap: break
        if E.winner(s) == seat: w += 1
    return w / G


def pol_move(s):
    pri, _ = ev(s)
    return max(pri.items(), key=lambda kv: kv[1])[0] if pri else -1


# 価値の健全性：空盤の価値（≒0が正常）と、明らかに勝ってる局面の価値
def value_sanity():
    s = E.make_game(N, 2)
    _, v0 = ev(s)
    s2 = E.make_game(N, 2)
    for _ in range(8):  # P1 に何手か入れて P1 優勢にする
        lm = E.legal_moves(s2, s2.turn)
        if not lm: break
        E.play(s2, BL.greedy_move(s2, rng) if s2.turn == 1 else lm[0], s2.turn)
    _, v2 = ev(s2)
    return v0, v2


print(f'ckpt={ckpt} N={N} G={G} device={device}')
v0, v2 = value_sanity()
print(f'価値: 空盤={v0:+.2f}(≒0が正常) / 数手後={v2:+.2f}')
print(f'生policy(探索なし)  vs 貪欲: 勝率 {vs_greedy(pol_move):.2f}')
for sims in SIMS:
    print(f'網-MCTS sims={sims:<4} vs 貪欲: 勝率 {vs_greedy(lambda s, S=sims: MC.pick_move(MC.search(s, ev, S, rng=rng), 0.0, rng)):.2f}')
