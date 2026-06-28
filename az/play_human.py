"""人間 vs AI でキリシマを対局する（ターミナル）。
AI は学習網（--ai net）／捕獲貪欲（greedy）／乱択（random）から選べる。
盤・入力・ルールは torch 不要。net のときだけ torch を読む。

使い方:
  python play_human.py                       # net_latest.pt と対局・自分が先手(1)
  python play_human.py ckpt/net_peak_r46.pt  # 網を指定
  python play_human.py ckpt/net_peak_r46.pt 7 2 800   # N=7・自分が後手(2)・網のsims=800
  python play_human.py x 7 1 0 greedy        # 網無しで捕獲貪欲と対局（手元検証用）
引数: [ckpt] [N=7] [自分の席=1] [sims=400] [ai=net|greedy|random]
"""
import sys, random
import engine as E

ckpt = sys.argv[1] if len(sys.argv) > 1 else 'ckpt/net_latest.pt'
N = int(sys.argv[2]) if len(sys.argv) > 2 else 7
ME = int(sys.argv[3]) if len(sys.argv) > 3 else 1      # 自分の席（1=先手 / 2=後手）
SIMS = int(sys.argv[4]) if len(sys.argv) > 4 else 400
AI = sys.argv[5] if len(sys.argv) > 5 else 'net'
AIP = 2 if ME == 1 else 1
rng = random.Random()


def decode(mid):
    hc = E.HC(N)
    if mid < hc: return ('H', mid % (N - 1), mid // (N - 1))
    v = mid - hc; return ('V', v % N, v // N)


def render(s):
    M = s.M; out = []
    head = '   ' + ''.join(f'{x:^4}' for x in range(N))      # x座標
    out.append(head)
    for y in range(N):
        row = f'{y:2} '
        for x in range(N):
            row += '·'
            if x < N - 1:
                p = s.H[y * (N - 1) + x]
                row += f'─{p}─' if p else '   '
        out.append(row)
        if y < N - 1:
            row = '   '
            for x in range(N):
                p = s.V[y * N + x]
                row += str(p) if p else ' '
                if x < N - 1:
                    c = s.cells[y * M + x]
                    row += f' {c} ' if c else '   '
            out.append(row)
    return '\n'.join(out)


def show_moves(s, p):
    mv = E.legal_moves(s, p)
    rows = [(mid, E.capture_gain(s, mid)) for mid in mv]
    rows.sort(key=lambda r: -r[1])      # 捕獲手を上に
    print(f'  打てる手（{len(rows)}）。番号で選ぶ。捕獲できる手は ★+n :')
    line = []
    for i, (mid, g) in enumerate(rows):
        t, x, yy = decode(mid)
        tag = f' ★+{g}' if g else ''
        line.append(f'[{i:2}] {t}({x},{yy}){tag}')
    # 4列で表示
    for i in range(0, len(line), 4):
        print('   ' + '   '.join(f'{c:18}' for c in line[i:i + 4]))
    return [mid for mid, _ in rows]


def human_move(s):
    order = show_moves(s, ME)
    while True:
        raw = input('  あなたの手 番号> ').strip()
        if raw in ('q', 'quit'): sys.exit('中断')
        if raw.isdigit() and 0 <= int(raw) < len(order): return order[int(raw)]
        print('  番号が不正。打てる手の番号を入れて。')


def make_ai():
    if AI == 'random':
        return lambda s: rng.choice(E.legal_moves(s, AIP))
    if AI == 'greedy':
        import baseline as BL
        return lambda s: BL.greedy_move(s, rng)
    # net
    import torch, model as MD, mcts as MC
    dev = 'cuda' if torch.cuda.is_available() else 'cpu'
    net = MD.Net(N).to(dev); net.load_state_dict(torch.load(ckpt, map_location=dev)); net.eval()
    ev = MD.make_evaluator(net, dev)
    print(f'  網 {ckpt} を {dev} で読み込み（sims={SIMS}）')
    return lambda s: MC.pick_move(MC.search(s, ev, SIMS, rng=rng), 0.0, rng)


def main():
    print(f'=== キリシマ  あなた=席{ME}  AI({AI})=席{AIP}  N={N} ===')
    ai_move = make_ai()
    s = E.make_game(N, 2)
    while s.turn != 0:
        print('\n' + render(s))
        print(f'  得点  あなた(席{ME})={s.score[ME]}  AI(席{AIP})={s.score[AIP]}   手数{s.moves}')
        if s.turn == ME:
            mid = human_move(s)
            g = E.play(s, mid, ME)
            t, x, y = decode(mid); print(f'  → あなた {t}({x},{y})' + (f'  +{g}捕獲！' if g else ''))
        else:
            mid = ai_move(s)
            if mid is None or mid < 0: break
            g = E.play(s, mid, AIP)
            t, x, y = decode(mid); print(f'  → AI {t}({x},{y})' + (f'  +{g}捕獲' if g else ''))
    print('\n' + render(s))
    a, b = s.score[ME], s.score[AIP]
    print(f'\n=== 終局  あなた {a} - {b} AI ===')
    print('  ' + ('あなたの勝ち！' if a > b else 'AIの勝ち' if b > a else '引き分け'))


if __name__ == '__main__':
    main()
