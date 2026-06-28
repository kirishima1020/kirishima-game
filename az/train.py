"""キリシマ AlphaZero 学習。
  1) ウォームスタート：ver2+ の教師対局を模倣（behavior cloning）→ 一気に ver2+ 並みへ。
  2) 自己対局：網-MCTS で打ち、(局面, MCTS訪問分布, 勝敗) を貯めて網を磨く。世代反復。
  チェックポイントを逐次保存。進捗は「網-MCTS vs 捕獲貪欲」勝率で表示。

使い方:
  python train.py --smoke                # 数分で一周（CPUでも動作確認）
  python train.py --hours 3 --N 7        # 本番（Runpod GPU 推奨）
"""
import argparse, json, time, os, random, collections
import numpy as np
import torch
import torch.nn.functional as F
import engine as E
import mcts as MC
import model as MD
import baseline as BL


def parse():
    ap = argparse.ArgumentParser()
    ap.add_argument('--N', type=int, default=7)
    ap.add_argument('--hours', type=float, default=3.0)
    ap.add_argument('--teacher', default='teacher.ndjson')
    ap.add_argument('--out', default='ckpt')
    ap.add_argument('--sims', type=int, default=64)
    ap.add_argument('--games-per-round', type=int, default=24)
    ap.add_argument('--batch', type=int, default=256)
    ap.add_argument('--train-steps', type=int, default=200)
    ap.add_argument('--buffer', type=int, default=80000)
    ap.add_argument('--warm-epochs', type=int, default=8)
    ap.add_argument('--lr', type=float, default=1e-3)
    ap.add_argument('--smoke', action='store_true')
    return ap.parse_args()


def value_target(w, mover):
    return 0.0 if w == 0 else (1.0 if w == mover else -1.0)


def teacher_samples(path, N):
    EC = E.EC(N); out = []
    if not os.path.exists(path):
        print('[warn] teacher not found:', path); return out
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line: continue
            g = json.loads(line)
            if g.get('N') != N: continue
            s = E.make_game(N, 2); w = g['winner']
            for mid in g['ids']:
                mover = s.turn
                pol = np.zeros(EC, dtype=np.float32); pol[mid] = 1.0
                out.append((E.planes(s), pol, value_target(w, mover)))
                E.play(s, mid, mover)
    return out


def selfplay_game(N, ev, sims, rng, temp_moves=12):
    EC = E.EC(N); s = E.make_game(N, 2); hist = []; cap = (N - 1) * (N - 1) * 4 + 60
    while s.turn != 0:
        visits = MC.search(s, ev, sims, dirichlet=0.3, rng=rng)
        if not visits: break
        pol = np.zeros(EC, dtype=np.float32); tot = sum(visits.values()) or 1
        for mid, n in visits.items(): pol[mid] = n / tot
        hist.append((E.planes(s), pol, s.turn))
        mv = MC.pick_move(visits, 1.0 if s.moves < temp_moves else 0.0, rng)
        E.play(s, mv, s.turn)
        if s.moves > cap: break
    w = E.winner(s)
    return [(pl, pol, value_target(w, mover)) for pl, pol, mover in hist]


def train_on(net, opt, buf, device, steps, batch):
    if len(buf) < batch: return None
    net.train(); ps = vs = 0.0
    for _ in range(steps):
        idx = np.random.randint(0, len(buf), size=batch)
        X = torch.from_numpy(np.stack([buf[i][0] for i in idx])).to(device)
        P = torch.from_numpy(np.stack([buf[i][1] for i in idx])).to(device)
        Vt = torch.tensor([buf[i][2] for i in idx], dtype=torch.float32, device=device)
        logits, v = net(X)
        ploss = -(P * F.log_softmax(logits, dim=1)).sum(1).mean()
        vloss = F.mse_loss(v, Vt)
        (ploss + vloss).backward(); opt.step(); opt.zero_grad()
        ps += float(ploss); vs += float(vloss)
    return ps / steps, vs / steps


def eval_net_vs_greedy(net_ev, N, sims, games, rng):
    w = 0
    for g in range(games):
        net_seat = (g % 2) + 1; s = E.make_game(N, 2); cap = (N - 1) * (N - 1) * 4 + 60
        while s.turn != 0:
            if s.turn == net_seat:
                mv = MC.pick_move(MC.search(s, net_ev, sims, rng=rng), 0.0, rng)
            else:
                mv = BL.greedy_move(s, rng)
            if mv < 0: break
            E.play(s, mv, s.turn)
            if s.moves > cap: break
        if E.winner(s) == net_seat: w += 1
    return w / games


def main():
    a = parse()
    if a.smoke:
        a.hours, a.games_per_round, a.train_steps, a.warm_epochs, a.sims = 0.03, 2, 10, 1, 16
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f'device={device} N={a.N} sims={a.sims} hours={a.hours}', flush=True)
    os.makedirs(a.out, exist_ok=True)
    rng = random.Random(12345)
    net = MD.Net(a.N).to(device)
    opt = torch.optim.Adam(net.parameters(), lr=a.lr, weight_decay=1e-4)
    net_ev = MD.make_evaluator(net, device)

    # 1) ウォームスタート（教師模倣）
    ts = teacher_samples(a.teacher, a.N)
    print(f'teacher samples = {len(ts)}', flush=True)
    if ts:
        for ep in range(a.warm_epochs):
            r = train_on(net, opt, ts, device, max(1, len(ts) // a.batch), a.batch)
            if r: print(f'  warm ep{ep+1}: ploss={r[0]:.3f} vloss={r[1]:.3f}', flush=True)
        torch.save(net.state_dict(), os.path.join(a.out, 'net_warm.pt'))
        wr = eval_net_vs_greedy(net_ev, a.N, max(48, a.sims), 2 if a.smoke else 6, rng)
        print(f'  [eval ウォームスタート後] 網-MCTS vs 捕獲貪欲 勝率 = {wr:.2f}', flush=True)

    # 2) 自己対局ループ
    buf = collections.deque(maxlen=a.buffer); buf.extend(ts)
    t0 = time.time(); rnd = 0
    while time.time() - t0 < a.hours * 3600:
        rnd += 1
        for _ in range(a.games_per_round):
            buf.extend(selfplay_game(a.N, net_ev, a.sims, rng))
        r = train_on(net, opt, buf, device, a.train_steps, a.batch)
        el = (time.time() - t0) / 60
        line = f'round {rnd} t={el:.1f}m buf={len(buf)}'
        if r: line += f' ploss={r[0]:.3f} vloss={r[1]:.3f}'
        print(line, flush=True)
        torch.save(net.state_dict(), os.path.join(a.out, 'net_latest.pt'))
        if rnd % 3 == 0 or a.smoke:
            wr = eval_net_vs_greedy(net_ev, a.N, max(48, a.sims), 2 if a.smoke else 6, rng)
            print(f'  [eval] 網-MCTS vs 捕獲貪欲 勝率 = {wr:.2f}', flush=True)
        if a.smoke: break
    torch.save(net.state_dict(), os.path.join(a.out, 'net_final.pt'))
    print('done ->', os.path.join(a.out, 'net_final.pt'), flush=True)


if __name__ == '__main__':
    main()
