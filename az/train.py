"""キリシマ AlphaZero 学習（並列自己対局）。
  1) ウォームスタート：ver2+ 教師を模倣 → 一気に ver2+ 並み。
  2) 自己対局：複数コアで並列に網-MCTS 対局 → (局面, MCTS訪問分布, 勝敗) を貯めて磨く。
  メインで学習（GPUあれば使うが、網が極小なのでCPUでも十分。要はコア数）。逐次チェックポイント。

使い方:
  python train.py --smoke                         # 数分で動作確認
  python train.py --hours 1 --N 7 --workers 30    # 32コア箱で1時間
  python train.py --hours 3 --N 7 --shutdown      # 終了後にポッド停止（要・永続保存先）

torch非依存（engine/mcts/numpy/multiprocessing）を上に置き、torch/model は実行時に読む
（並列プラミングをスタブでローカル検証できるように）。
"""
import argparse, json, time, os, random, collections
import multiprocessing as mp
import numpy as np
import engine as E
import mcts as MC
import baseline as BL

# --- 自己対局（torch非依存。評価器はモジュールグローバルで fork 継承）---
_EVAL = None; _N = None; _SIMS = None


def value_target(w, mover):
    return 0.0 if w == 0 else (1.0 if w == mover else -1.0)


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


def _play_chunk(args):
    n_games, seed = args
    rng = random.Random(seed); out = []
    for _ in range(n_games):
        out.extend(selfplay_game(_N, _EVAL, _SIMS, rng))
    return out


def _winit():
    try:
        import torch; torch.set_num_threads(1)   # ワーカは1スレッド（過剰購読回避）。torch無くても可。
    except Exception:
        pass


def parallel_selfplay(games_per_worker, workers, base_seed):
    chunks = [(games_per_worker, base_seed + i * 7919) for i in range(workers)]
    if workers <= 1:
        out = []
        for c in chunks: out.extend(_play_chunk(c))
        return out
    with mp.Pool(workers, initializer=_winit) as pool:   # fork: ワーカは現在の _EVAL(net) を継承
        res = pool.map(_play_chunk, chunks)
    out = []
    for r in res: out.extend(r)
    return out


# --- 以下 torch 必須（main から呼ぶ）---
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


def eval_net_vs_greedy(net_ev, N, sims, games, rng):
    w = 0
    for g in range(games):
        seat = (g % 2) + 1; s = E.make_game(N, 2); cap = (N - 1) * (N - 1) * 4 + 60
        while s.turn != 0:
            mv = MC.pick_move(MC.search(s, net_ev, sims, rng=rng), 0.0, rng) if s.turn == seat else BL.greedy_move(s, rng)
            if mv < 0: break
            E.play(s, mv, s.turn)
            if s.moves > cap: break
        if E.winner(s) == seat: w += 1
    return w / games


def parse():
    ap = argparse.ArgumentParser()
    ap.add_argument('--N', type=int, default=7)
    ap.add_argument('--hours', type=float, default=3.0)
    ap.add_argument('--teacher', default='teacher.ndjson')
    ap.add_argument('--out', default='ckpt')
    ap.add_argument('--sims', type=int, default=64)
    ap.add_argument('--workers', type=int, default=0)          # 0=自動(コア-2)
    ap.add_argument('--games-per-worker', type=int, default=2)
    ap.add_argument('--batch', type=int, default=256)
    ap.add_argument('--train-steps', type=int, default=200)
    ap.add_argument('--buffer', type=int, default=120000)
    ap.add_argument('--warm-epochs', type=int, default=8)
    ap.add_argument('--lr', type=float, default=1e-3)
    ap.add_argument('--shutdown', action='store_true')
    ap.add_argument('--smoke', action='store_true')
    return ap.parse_args()


def main():
    global _EVAL, _N, _SIMS
    try: mp.set_start_method('fork')   # ワーカが親の網(_EVAL)を継承するため。Linux既定・macも可。
    except RuntimeError: pass
    a = parse()
    if a.smoke:
        a.hours, a.games_per_worker, a.train_steps, a.warm_epochs, a.sims, a.workers = 0.03, 1, 10, 1, 16, 2
    if a.workers <= 0:
        a.workers = max(1, (os.cpu_count() or 4) - 2)

    import torch
    import torch.nn.functional as F
    import model as MD
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f'device={device} N={a.N} sims={a.sims} workers={a.workers} hours={a.hours}', flush=True)
    os.makedirs(a.out, exist_ok=True)
    rng = random.Random(12345)

    net = MD.Net(a.N).to(device)                 # 学習用
    net_cpu = MD.Net(a.N)                          # 自己対局用（CPU・fork安全）
    opt = torch.optim.Adam(net.parameters(), lr=a.lr, weight_decay=1e-4)
    _N, _SIMS = a.N, a.sims
    _EVAL = MD.make_evaluator(net_cpu, 'cpu')

    def cpu_state():
        return {k: v.detach().cpu() for k, v in net.state_dict().items()}

    def train_on(buf, steps):
        if len(buf) < a.batch: return None
        net.train(); ps = vs = 0.0
        for _ in range(steps):
            idx = np.random.randint(0, len(buf), size=a.batch)
            X = torch.from_numpy(np.stack([buf[i][0] for i in idx])).to(device)
            P = torch.from_numpy(np.stack([buf[i][1] for i in idx])).to(device)
            Vt = torch.tensor([buf[i][2] for i in idx], dtype=torch.float32, device=device)
            logits, v = net(X)
            ploss = -(P * F.log_softmax(logits, dim=1)).sum(1).mean()
            vloss = F.mse_loss(v, Vt)
            (ploss + vloss).backward(); opt.step(); opt.zero_grad()
            ps += float(ploss); vs += float(vloss)
        return ps / steps, vs / steps

    def save(name):
        torch.save(net.state_dict(), os.path.join(a.out, name))

    # 1) ウォームスタート
    ts = teacher_samples(a.teacher, a.N)
    print(f'teacher samples = {len(ts)}', flush=True)
    if ts:
        for ep in range(a.warm_epochs):
            r = train_on(ts, max(1, len(ts) // a.batch))
            if r: print(f'  warm ep{ep+1}: ploss={r[0]:.3f} vloss={r[1]:.3f}', flush=True)
        save('net_warm.pt')
        net_cpu.load_state_dict(cpu_state())
        wr = eval_net_vs_greedy(_EVAL, a.N, max(48, a.sims), 2 if a.smoke else 6, rng)
        print(f'  [eval ウォームスタート後] 網-MCTS vs 捕獲貪欲 勝率 = {wr:.2f}', flush=True)

    # 2) 並列自己対局ループ
    buf = collections.deque(maxlen=a.buffer); buf.extend(ts)
    t0 = time.time(); rnd = 0
    while time.time() - t0 < a.hours * 3600:
        rnd += 1
        net_cpu.load_state_dict(cpu_state())                 # 自己対局網に最新重みを反映（fork前）
        samples = parallel_selfplay(a.games_per_worker, a.workers, rng.randrange(1 << 30))
        buf.extend(samples)
        r = train_on(buf, a.train_steps)
        el = (time.time() - t0) / 60
        line = f'round {rnd} t={el:.1f}m games={a.workers*a.games_per_worker} buf={len(buf)}'
        if r: line += f' ploss={r[0]:.3f} vloss={r[1]:.3f}'
        print(line, flush=True)
        save('net_latest.pt')
        if rnd % 3 == 0 or a.smoke:
            net_cpu.load_state_dict(cpu_state())
            wr = eval_net_vs_greedy(_EVAL, a.N, max(48, a.sims), 2 if a.smoke else 6, rng)
            print(f'  [eval] 網-MCTS vs 捕獲貪欲 勝率 = {wr:.2f}', flush=True)
        if a.smoke: break
    save('net_final.pt')
    print('done ->', os.path.join(a.out, 'net_final.pt'), flush=True)

    if a.shutdown:
        pod = os.environ.get('RUNPOD_POD_ID', '')
        print(f'shutting down pod {pod} ...', flush=True)
        os.system(f'runpodctl stop pod {pod}') if pod else os.system('shutdown -h now')


if __name__ == '__main__':
    main()
