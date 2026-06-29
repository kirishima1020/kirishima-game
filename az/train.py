"""キリシマ AlphaZero 学習（並列自己対局・安定化版）。
  1) ウォームスタート：ver2+ 教師を模倣。
  2) 並列自己対局（30コア）で (局面, MCTS訪問分布, 勝敗) を貯めて磨く。
  安定化：学習率↓＋勾配クリップ＋**教師を毎バッチに混ぜ続ける**（退行防止）＋自己対局 sims↑。
  評価は GPU網で低頻度（本筋を食わない）。逐次チェックポイント。

使い方:
  python train.py --smoke
  python train.py --hours 1 --N 7 --workers 30
"""
import argparse, json, time, os, random, collections
import multiprocessing as mp
import numpy as np
import engine as E
import mcts as MC
import baseline as BL
import solve as SV

# --- 自己対局（torch非依存。評価器はモジュールグローバルで fork 継承）---
_EVAL = None; _N = None; _SIMS = None; _ECELLS = 0; _ENODES = 0


def value_target(w, mover):
    return 0.0 if w == 0 else (1.0 if w == mover else -1.0)


def selfplay_game(N, ev, sims, rng, temp_moves=14, ecells=0, enodes=0):
    EC = E.EC(N); s = E.make_game(N, 2); hist = []; cap = (N - 1) * (N - 1) * 4 + 60
    exact_w = None
    while s.turn != 0:
        # 終盤に入ったら厳密ソルバの勝敗で打ち切る（弱い網での雑な打ち切りを真理で置換）。
        # 予算超過（枝が多すぎ）なら None が返り、通常どおり自己対局を続ける。
        if ecells:
            ev_res = SV.endgame_value(s, max_cells=ecells, max_nodes=enodes)
            if ev_res is not None:
                exact_w = ev_res[0]; break
        visits = MC.search(s, ev, sims, dirichlet=0.3, rng=rng)
        if not visits: break
        pol = np.zeros(EC, dtype=np.float32); tot = sum(visits.values()) or 1
        for mid, n in visits.items(): pol[mid] = n / tot
        hist.append((E.planes(s), pol, s.turn))
        mv = MC.pick_move(visits, 1.0 if s.moves < temp_moves else 0.0, rng)
        E.play(s, mv, s.turn)
        if s.moves > cap: break
    w = exact_w if exact_w is not None else E.winner(s)
    return [(pl, pol, value_target(w, mover)) for pl, pol, mover in hist]


def _play_chunk(args):
    n_games, seed = args
    rng = random.Random(seed); out = []
    for _ in range(n_games):
        out.extend(selfplay_game(_N, _EVAL, _SIMS, rng, ecells=_ECELLS, enodes=_ENODES))
    return out


def _winit():
    try:
        import torch; torch.set_num_threads(1)
    except Exception:
        pass


def parallel_selfplay(games_per_worker, workers, base_seed):
    chunks = [(games_per_worker, base_seed + i * 7919) for i in range(workers)]
    if workers <= 1:
        out = []
        for c in chunks: out.extend(_play_chunk(c))
        return out
    with mp.Pool(workers, initializer=_winit) as pool:
        res = pool.map(_play_chunk, chunks)
    out = []
    for r in res: out.extend(r)
    return out


# --- 以下 torch 必須 ---
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


def rollout_evaluator(smart, rng):
    """MCTS用の葉評価をロールアウトで（捕獲認識MCTSの中身）。priors=一様, value=プレイアウト勝敗。"""
    def ev(s):
        lm = E.legal_moves(s, s.turn)
        pri = {m: 1.0 / len(lm) for m in lm} if lm else {}
        who = s.turn; c = s.clone()
        while c.turn != 0:
            lm2 = E.legal_moves(c, c.turn)
            if not lm2: break
            if smart:
                samp = lm2 if len(lm2) <= 12 else rng.sample(lm2, 12)
                bg, bm = 0, None
                for m in samp:
                    g = E.capture_gain(c, m)
                    if g > bg: bg, bm = g, m
                mv = bm if bm is not None else rng.choice(lm2)
            else:
                mv = rng.choice(lm2)
            E.play(c, mv, c.turn)
        w = E.winner(c)
        return pri, (0.0 if w == 0 else 1.0 if w == who else -1.0)
    return ev


def eval_net_vs(net_ev, opp_move, N, sims, games, rng):
    """網-MCTS vs 任意の相手手関数。網の勝率を返す。"""
    w = 0
    for g in range(games):
        seat = (g % 2) + 1; s = E.make_game(N, 2); cap = (N - 1) * (N - 1) * 4 + 60
        while s.turn != 0:
            mv = MC.pick_move(MC.search(s, net_ev, sims, rng=rng), 0.0, rng) if s.turn == seat else opp_move(s)
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
    ap.add_argument('--sims', type=int, default=200)
    ap.add_argument('--workers', type=int, default=0)
    ap.add_argument('--games-per-worker', type=int, default=2)
    ap.add_argument('--batch', type=int, default=256)
    ap.add_argument('--train-steps', type=int, default=150)
    ap.add_argument('--buffer', type=int, default=150000)
    ap.add_argument('--warm-epochs', type=int, default=20)
    ap.add_argument('--lr', type=float, default=1e-3)   # 強いwarmのため戻す。自己対局の安定は教師アンカー+クリップが担う
    ap.add_argument('--clip', type=float, default=10.0)   # 暴れ防止の保険のみ。安定の主役は教師アンカー。1.0は絞りすぎて学習が死ぬ
    ap.add_argument('--teacher-frac', type=float, default=0.3)   # 教師アンカー初期値（退行防止）
    ap.add_argument('--teacher-anneal', type=int, default=25)    # この round 数で 0.3→0.05 へ減衰（教師超えを許す）
    ap.add_argument('--eval-every', type=int, default=20)        # 評価頻度（ラウンド）
    ap.add_argument('--eval-games', type=int, default=4)
    ap.add_argument('--eval-opp', choices=['greedy', 'champion'], default='champion')  # 評価相手。championは捕獲認識MCTS
    ap.add_argument('--champ-sims', type=int, default=120)   # 評価相手(捕獲認識MCTS)の探索数。重いので控えめ
    ap.add_argument('--endgame-cells', type=int, default=9)      # 空きセル≤これで終盤ソルバ起動（0で無効）
    ap.add_argument('--endgame-nodes', type=int, default=60000)  # ソルバのノード予算（超で網に退避し詰まらせない）
    ap.add_argument('--shutdown', action='store_true')
    ap.add_argument('--smoke', action='store_true')
    ap.add_argument('--diag', action='store_true')   # warm網の強さ分析だけして終了（長時間回す価値の判定）
    return ap.parse_args()


def main():
    global _EVAL, _N, _SIMS, _ECELLS, _ENODES
    try: mp.set_start_method('fork')
    except RuntimeError: pass
    a = parse()
    if a.smoke:
        a.hours, a.games_per_worker, a.train_steps, a.warm_epochs, a.sims, a.workers, a.eval_every = 0.05, 1, 10, 2, 16, 2, 1
    if a.workers <= 0:
        a.workers = max(1, (os.cpu_count() or 4) - 2)

    import torch
    import torch.nn.functional as F
    import model as MD
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f'device={device} N={a.N} sims={a.sims} workers={a.workers} lr={a.lr} t-frac={a.teacher_frac} hours={a.hours}', flush=True)
    os.makedirs(a.out, exist_ok=True)
    rng = random.Random(12345)

    net = MD.Net(a.N).to(device)        # 学習用（GPU）
    net_cpu = MD.Net(a.N)               # 自己対局用（CPU・fork安全）
    opt = torch.optim.Adam(net.parameters(), lr=a.lr, weight_decay=1e-4)
    _N, _SIMS = a.N, a.sims
    _ECELLS, _ENODES = a.endgame_cells, a.endgame_nodes
    print(f'endgame solver: cells<={_ECELLS} budget={_ENODES} nodes', flush=True)
    _EVAL = MD.make_evaluator(net_cpu, 'cpu')       # ワーカ用（CPU）
    eval_ev = MD.make_evaluator(net, device)        # 評価用（GPU・速い）

    def cpu_state():
        return {k: v.detach().cpu() for k, v in net.state_dict().items()}

    def train_on(buf, teacher, steps, tfrac):
        if len(buf) < a.batch: return None
        net.train(); ps = vs = 0.0
        nt = int(a.batch * tfrac) if teacher else 0
        nb = a.batch - nt
        for _ in range(steps):
            samp = []
            if nt:
                for i in np.random.randint(0, len(teacher), nt): samp.append(teacher[i])
            for i in np.random.randint(0, len(buf), nb): samp.append(buf[i])
            X = torch.from_numpy(np.stack([s[0] for s in samp])).to(device)
            P = torch.from_numpy(np.stack([s[1] for s in samp])).to(device)
            Vt = torch.tensor([s[2] for s in samp], dtype=torch.float32, device=device)
            logits, v = net(X)
            ploss = -(P * F.log_softmax(logits, dim=1)).sum(1).mean()
            vloss = F.mse_loss(v, Vt)
            (ploss + vloss).backward()
            torch.nn.utils.clip_grad_norm_(net.parameters(), a.clip)
            opt.step(); opt.zero_grad()
            ps += float(ploss); vs += float(vloss)
        return ps / steps, vs / steps

    if a.eval_opp == 'champion':
        _champ_ev = rollout_evaluator(True, rng)
        _opp = lambda s: MC.pick_move(MC.search(s, _champ_ev, a.champ_sims, rng=rng), 0.0, rng)
        _opp_label = f'捕獲認識MCTS({a.champ_sims})'
    else:
        _opp = lambda s: BL.greedy_move(s, rng)
        _opp_label = '捕獲貪欲'

    def do_eval(tag):
        net_cpu.load_state_dict(cpu_state())  # （ワーカ網も最新化）
        wr = eval_net_vs(eval_ev, _opp, a.N, a.sims, 2 if a.smoke else a.eval_games, rng)
        print(f'  [eval {tag}] 網-MCTS vs {_opp_label} 勝率 = {wr:.2f}', flush=True)

    # 1) ウォームスタート（教師模倣）
    ts = teacher_samples(a.teacher, a.N)
    print(f'teacher samples = {len(ts)}', flush=True)
    if ts:
        for ep in range(a.warm_epochs):
            r = train_on(ts, None, max(1, len(ts) // a.batch), 0.0)
            if r and (ep % 4 == 3 or ep == a.warm_epochs - 1):
                print(f'  warm ep{ep+1}: ploss={r[0]:.3f} vloss={r[1]:.3f}', flush=True)
        torch.save(net.state_dict(), os.path.join(a.out, 'net_warm.pt'))
        do_eval('warm後')

    if a.diag:
        print('[diag] warm網の強さ分析（vs 捕獲貪欲・各6局）。smart-500は貪欲を1.00で粉砕する＝これが合格基準。', flush=True)
        base = MD.make_evaluator(net, device)
        def noval(s):
            p, _ = base(s); return p, 0.0   # 価値を0に＝policyのみで探索
        for sims in (64, 256, 1024):
            print(f'  sims={sims} 価値あり: 勝率={eval_net_vs_greedy(eval_ev, a.N, sims, 6, rng):.2f}', flush=True)
        print(f'  sims=256 価値なし(policyのみ): 勝率={eval_net_vs_greedy(noval, a.N, 256, 6, rng):.2f}', flush=True)
        print('[読み] simsを上げて勝率↑→探索不足(高sims+長時間で解決)。flat→価値/MCTSが壊れ。'
              ' 価値なし>価値あり→価値が害(バグ)。', flush=True)
        return

    # 2) 並列自己対局ループ（教師アンカー混ぜ）
    buf = collections.deque(maxlen=a.buffer)
    t0 = time.time(); rnd = 0
    while time.time() - t0 < a.hours * 3600:
        rnd += 1
        net_cpu.load_state_dict(cpu_state())
        buf.extend(parallel_selfplay(a.games_per_worker, a.workers, rng.randrange(1 << 30)))
        tfrac = max(0.05, a.teacher_frac * (1 - rnd / a.teacher_anneal))   # アンカー減衰：教師超えを許す
        r = train_on(buf, ts, a.train_steps, tfrac)
        el = (time.time() - t0) / 60
        line = f'round {rnd} t={el:.1f}m tf={tfrac:.2f} games={a.workers*a.games_per_worker} buf={len(buf)}'
        if r: line += f' ploss={r[0]:.3f} vloss={r[1]:.3f}'
        print(line, flush=True)
        torch.save(net.state_dict(), os.path.join(a.out, 'net_latest.pt'))
        if rnd % a.eval_every == 0 or a.smoke:
            do_eval(f'r{rnd}')
        if a.smoke: break
    torch.save(net.state_dict(), os.path.join(a.out, 'net_final.pt'))
    print('done ->', os.path.join(a.out, 'net_final.pt'), flush=True)

    if a.shutdown:
        pod = os.environ.get('RUNPOD_POD_ID', '')
        print(f'shutting down pod {pod} ...', flush=True)
        os.system(f'runpodctl stop pod {pod}') if pod else os.system('shutdown -h now')


if __name__ == '__main__':
    main()
