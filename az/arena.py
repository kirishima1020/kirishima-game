"""2人戦ボットの総当たり。全ボットを同じ MCTS(mcts.py) で走らせ、葉の評価器だけ差し替える
（網＝価値評価、捕獲認識／乱択＝ロールアウト評価、1手最大捕獲＝探索なし）。探索条件を揃えた公平比較。
  python arena.py [ckpt=~/net_peak_r46.pt] [N=7] [sims=160] [games=4] [ecells=12]
Python のロールアウトは重いので、捕獲認識MCTS だけ sims を半分にしている（表に明記）。
"""
import sys, os, random, itertools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine as E, baseline as BL, mcts as MC, solve as SV

ckpt = os.path.expanduser(sys.argv[1]) if len(sys.argv) > 1 else os.path.expanduser('~/net_peak_r46.pt')
N = int(sys.argv[2]) if len(sys.argv) > 2 else 7
SIMS = int(sys.argv[3]) if len(sys.argv) > 3 else 160
G = int(sys.argv[4]) if len(sys.argv) > 4 else 4
ECELLS = int(sys.argv[5]) if len(sys.argv) > 5 else 12
ROLL_SIMS = SIMS                    # 全MCTSを等simsで公平比較（ロールアウトは重いが正直に）
rng = random.Random(12345)


def rollout_eval(smart):
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


def mcts_player(ev, sims):
    return lambda s: MC.pick_move(MC.search(s, ev, sims, rng=rng), 0.0, rng)


players = [('1手最大捕獲', lambda s: BL.greedy_move(s, rng)),
           ('乱択MCTS', mcts_player(rollout_eval(False), SIMS)),
           (f'捕獲認識MCTS({ROLL_SIMS})', mcts_player(rollout_eval(True), ROLL_SIMS))]
try:
    import torch, model as MD
    dev = 'cuda' if torch.cuda.is_available() else 'cpu'
    net = MD.Net(N).to(dev); net.load_state_dict(torch.load(ckpt, map_location=dev)); net.eval()
    net_ev = MD.make_evaluator(net, dev)

    def hybrid(s):
        if SV.empty_cells(s) <= ECELLS:        # 終盤は厳密ソルバの手（solve_strong['move']）
            try:
                mv = SV.solve_strong(s, max_nodes=300_000)['move']
                if mv >= 0: return mv
            except Exception:
                pass                            # 予算超過などは網に退避
        return MC.pick_move(MC.search(s, net_ev, SIMS, rng=rng), 0.0, rng)
    players.append(('方策価値網', mcts_player(net_ev, SIMS)))
    players.append(('網+終盤ソルバ', hybrid))
    print(f'網 {ckpt} を {dev} で読み込み。')
except Exception as e:
    print('網を読み込めないので網抜きで実施:', repr(e))


def play(mv1, mv2):
    s = E.make_game(N, 2); fn = {1: mv1, 2: mv2}; cap = (N - 1) * (N - 1) * 4 + 60
    while s.turn != 0:
        m = fn[s.turn](s)
        if m is None or m < 0: break
        E.play(s, m, s.turn)
        if s.moves > cap: break
    return E.winner(s)


names = [p[0] for p in players]
wins = {n: 0.0 for n in names}; played = {n: 0 for n in names}
cell = {a: {b: '·' for b in names} for a in names}
print(f'総当たり N={N} sims={SIMS} games/pair={G}（席入替）…\n')
for (na, fa), (nb, fb) in itertools.combinations(players, 2):
    wa = wb = dr = 0
    for g in range(G):
        w = play(fa, fb) if g % 2 == 0 else (lambda r: 1 if r == 2 else 2 if r == 1 else 0)(play(fb, fa))
        if w == 1: wa += 1
        elif w == 2: wb += 1
        else: dr += 1
    wins[na] += wa + 0.5 * dr; wins[nb] += wb + 0.5 * dr
    played[na] += G; played[nb] += G
    cell[na][nb] = f'{wa}-{wb}-{dr}'; cell[nb][na] = f'{wb}-{wa}-{dr}'
    print(f'  {na:16} {wa}-{wb}-{dr} {nb}')

print('\n=== 序列（勝率＝勝点/対局数, 引分0.5） ===')
rank = sorted(names, key=lambda n: -wins[n] / max(1, played[n]))
for i, n in enumerate(rank, 1):
    print(f'  {i}. {n:18} 勝率 {wins[n]/max(1,played[n]):.2f}  ({wins[n]:.1f}/{played[n]})')
