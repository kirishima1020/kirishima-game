"""キリシマ AlphaZero 網（PyTorch）。盤 N×N の多チャンネル平面 -> 方策(全辺EC)＋価値(tanh, 手番視点)。
小盤なので小さく。N でサイズが決まる（入力 N×N・出力 EC=2N(N-1)）。
"""
import torch
import torch.nn as nn
import torch.nn.functional as F


class ResBlock(nn.Module):
    def __init__(self, ch):
        super().__init__()
        self.c1 = nn.Conv2d(ch, ch, 3, padding=1, bias=False); self.b1 = nn.BatchNorm2d(ch)
        self.c2 = nn.Conv2d(ch, ch, 3, padding=1, bias=False); self.b2 = nn.BatchNorm2d(ch)
    def forward(self, x):
        y = F.relu(self.b1(self.c1(x)))
        y = self.b2(self.c2(y))
        return F.relu(x + y)


class Net(nn.Module):
    def __init__(self, N, in_ch=7, ch=48, blocks=4):
        super().__init__()
        self.N = N
        self.EC = 2 * N * (N - 1)
        self.stem = nn.Sequential(nn.Conv2d(in_ch, ch, 3, padding=1, bias=False), nn.BatchNorm2d(ch), nn.ReLU())
        self.res = nn.Sequential(*[ResBlock(ch) for _ in range(blocks)])
        self.ph = nn.Sequential(nn.Conv2d(ch, 2, 1, bias=False), nn.BatchNorm2d(2), nn.ReLU(),
                                nn.Flatten(), nn.Linear(2 * N * N, self.EC))
        self.vh = nn.Sequential(nn.Conv2d(ch, 1, 1, bias=False), nn.BatchNorm2d(1), nn.ReLU(),
                                nn.Flatten(), nn.Linear(N * N, 64), nn.ReLU(), nn.Linear(64, 1), nn.Tanh())

    def forward(self, x):
        x = self.res(self.stem(x))
        return self.ph(x), self.vh(x).squeeze(-1)


def make_evaluator(net, device):
    """MCTS用 evaluate(state) -> (priors{move:prob over legal}, value in [-1,1] for state.turn)。単一局面評価。"""
    import numpy as np
    import engine as E

    def evaluate(s):
        pl = E.planes(s)  # (C,N,N) float32
        x = torch.from_numpy(pl).unsqueeze(0).to(device)
        net.eval()
        with torch.no_grad():
            logits, v = net(x)
        logits = logits[0].detach().cpu().numpy()
        val = float(v[0].detach().cpu())
        lm = E.legal_moves(s, s.turn)
        if not lm:
            return {}, val
        ml = np.array([logits[m] for m in lm], dtype=np.float64)
        ml -= ml.max()
        e = np.exp(ml); e /= e.sum()
        return {m: float(e[i]) for i, m in enumerate(lm)}, val

    return evaluate
