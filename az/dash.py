"""キリシマ AlphaZero 学習 ライブダッシュボード。
train.py を子プロセスで回し、その出力を食って端末に進捗をガチャガチャ描く。
標準ライブラリのみ（Runpod でそのまま動く）。train.py 本体には触らない。

使い方:
  python dash.py --hours 1 --N 7 --workers 30      # 学習しながら可視化（引数はtrain.pyにそのまま渡る）
  python dash.py --demo                             # 学習せずに見た目だけプレビュー
  python dash.py --selftest                         # パーサ確認（CI用・描画なし）
"""
import sys, os, re, time, threading, subprocess, collections, unicodedata
try:
    sys.stdout.reconfigure(encoding='utf-8')   # ロケールが C でも日本語を確実に出す（端末側が対応していれば）
except Exception:
    pass

C = dict(reset='\033[0m', bold='\033[1m', dim='\033[2m', cyan='\033[36m', green='\033[32m',
         yellow='\033[33m', mag='\033[35m', red='\033[31m', blue='\033[34m', white='\033[97m')
SPIN = '⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
BLOCKS = ' ▁▂▃▄▅▆▇█'
INNER = 58
ANSI_RE = re.compile(r'\033\[[0-9;?]*[a-zA-Z]')


def vwidth(s):
    """表示幅。ANSIは0、全角(W/F)は2、他は1。"""
    s = ANSI_RE.sub('', s)
    return sum(2 if unicodedata.east_asian_width(c) in 'WF' else 1 for c in s)


def row(content):
    """枠線つき1行。表示幅で右パディングを揃える。"""
    pad = INNER - vwidth(content)
    if pad < 0: pad = 0
    return f"{C['cyan']}│{C['reset']}{content}{' ' * pad}{C['cyan']}│{C['reset']}"

R_ROUND = re.compile(r'round (\d+) t=([\d.]+)m .*games=(\d+) buf=(\d+) ploss=([\d.]+) vloss=([\d.]+)')
R_EVAL = re.compile(r'\[eval ([^\]]+)\].*=\s*([\d.]+)')
R_WARM = re.compile(r'warm ep(\d+): ploss=([\d.]+) vloss=([\d.]+)')
R_TEACH = re.compile(r'teacher samples = (\d+)')
R_DEV = re.compile(r'device=(\S+) N=(\d+) sims=(\d+) workers=(\d+).* hours=([\d.]+)')
R_SOLVER = re.compile(r'endgame solver: cells<=(\d+) budget=(\d+)')
SKIP = ('UserWarning', 'detach', 'requires_grad', 'ps +=', 'Triggered internally')


def new_state():
    return dict(phase='起動中', device='', N=0, sims=0, workers=0, hours=0.0, teacher=0,
                solver='', rnd=0, games=0, ploss=collections.deque(maxlen=60),
                vloss=collections.deque(maxlen=60), evals=[], last_eval=None, warm_ep=0,
                last='', t0=time.time(), done=False)


def parse(line, st):
    line = line.rstrip('\n')
    if not line or any(s in line for s in SKIP):
        return
    st['last'] = line.strip()[:46]
    m = R_DEV.search(line)
    if m:
        st['device'], st['N'], st['sims'], st['workers'], st['hours'] = \
            m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4)), float(m.group(5))
        return
    m = R_SOLVER.search(line)
    if m: st['solver'] = f"cells≤{m.group(1)} / {int(m.group(2))//1000}k nodes"; return
    m = R_TEACH.search(line)
    if m: st['teacher'] = int(m.group(1)); return
    m = R_WARM.search(line)
    if m:
        st['phase'] = 'ウォームスタート（教師模倣）'; st['warm_ep'] = int(m.group(1))
        st['ploss'].append(float(m.group(2))); st['vloss'].append(float(m.group(3))); return
    m = R_ROUND.search(line)
    if m:
        st['phase'] = '自己対局ループ（厳密終盤ラベル）'; st['rnd'] = int(m.group(1))
        st['games'] += int(m.group(3))
        st['ploss'].append(float(m.group(5))); st['vloss'].append(float(m.group(6))); return
    m = R_EVAL.search(line)
    if m: v = float(m.group(2)); st['last_eval'] = v; st['evals'].append(v); return
    if 'done ->' in line: st['phase'] = '完了'; st['done'] = True


def spark(vals, w=40):
    vals = list(vals)[-w:]
    if not vals: return ' ' * w
    lo, hi = min(vals), max(vals); rng = hi - lo or 1.0
    return ''.join(BLOCKS[1 + int((v - lo) / rng * (len(BLOCKS) - 2))] for v in vals)


def spark01(vals, w=40):
    """勝率専用：0〜1の固定スケール（0に張り付けば底のまま、上がれば上がる）。"""
    vals = list(vals)[-w:]
    if not vals: return ' ' * w
    return ''.join(BLOCKS[1 + int(max(0.0, min(1.0, v)) * (len(BLOCKS) - 2))] for v in vals)


def bar(frac, w=30, fill='█', empty='░'):
    frac = max(0.0, min(1.0, frac)); n = int(frac * w)
    return fill * n + empty * (w - n)


def render(st, frame):
    el = time.time() - st['t0']
    tgt = st['hours'] * 3600 if st['hours'] else 0
    sp = SPIN[frame % len(SPIN)]
    gpm = st['games'] / (el / 60) if el > 1 else 0
    top = '─' * INNER
    L = [f"{C['bold']}{C['cyan']}╭{top}╮{C['reset']}"]
    L.append(row(f" {C['white']}{C['bold']}{sp} キリシマ AlphaZero  学習ライブ{C['reset']}"))
    L.append(f"{C['cyan']}├{top}┤{C['reset']}")
    L.append(row(f" {C['dim']}盤N={st['N']} sims={st['sims']} workers={st['workers']} dev={st['device']}{C['reset']}"))
    L.append(row(f" {C['dim']}終盤ソルバ {st['solver']}{C['reset']}"))
    pcol = C['green'] if st['done'] else C['yellow']
    L.append(row(f" {pcol}{C['bold']}▶ {st['phase']}{C['reset']}"))
    if tgt:
        L.append(row(f" 経過 {C['green']}{bar(min(1.0, el / tgt), 28)}{C['reset']} {int(el//60)}分/{int(tgt//60)}分"))
    else:
        L.append(row(f" 経過 {int(el//60)}分{int(el%60):02d}秒"))
    L.append(row(f" ラウンド {C['bold']}{st['rnd']}{C['reset']}  総対局 {C['bold']}{st['games']}{C['reset']}  速度 {gpm:.1f}局/分"))
    L.append(f"{C['cyan']}├{top}┤{C['reset']}")
    pl = st['ploss'][-1] if st['ploss'] else 0
    vl = st['vloss'][-1] if st['vloss'] else 0
    L.append(row(f" 方策損失 {C['mag']}{spark(st['ploss'], 38)}{C['reset']} {pl:5.2f}"))
    L.append(row(f" 価値損失 {C['blue']}{spark(st['vloss'], 38)}{C['reset']} {vl:5.3f}"))
    L.append(f"{C['cyan']}├{top}┤{C['reset']}")
    evs = st['evals']
    roll = sum(evs[-12:]) / len(evs[-12:]) if evs else None   # 直近12回の移動勝率
    rc = C['green'] if (roll or 0) >= 0.5 else (C['yellow'] if (roll or 0) > 0 else C['red'])
    rolltxt = f"{roll:.2f}" if roll is not None else "--"
    L.append(row(f" {C['bold']}勝率 網vs捕獲貪欲{C['reset']} {rc}{spark01(evs, 30)}{C['reset']} {rc}直近{rolltxt}{C['reset']}"))
    cur = f"{st['last_eval']:.2f}" if st['last_eval'] is not None else "--"
    L.append(row(f" {C['dim']}最新 {cur}  測定 {len(evs)} 回  ↑0.5線を越えれば捕獲貪欲を圧倒{C['reset']}"))
    L.append(f"{C['cyan']}├{top}┤{C['reset']}")
    L.append(row(f" {C['dim']}log:{C['reset']} {st['last']}"))
    L.append(f"{C['cyan']}├{top}┤{C['reset']}")
    L.append(row(f" {C['dim']}Ctrl-B→P パネル⇄シェル  Ctrl-B→L 学習へ  Ctrl-B→D 裏へ  Ctrl-C 停止{C['reset']}"))
    L.append(f"{C['bold']}{C['cyan']}╰{top}╯{C['reset']}")
    return '\n'.join(x + '\033[K' for x in L)


ALT_ON = '\033[?1049h\033[2J\033[?25l'   # 代替スクリーンに入る・全消し・カーソル隠す
ALT_OFF = '\033[?25h\033[?1049l'          # カーソル戻す・元画面（シェル）に復帰


def loop(get_line, st):
    # 代替スクリーンに切替＝ダッシュ専用のまっさらな画面に固定表示。抜けると元のシェルが戻る。
    # 塗り直しは「変化時＋0.5秒ごと」に抑える。
    sys.stdout.write(ALT_ON)
    frame = 0; last_paint = 0.0
    try:
        while True:
            line = get_line()
            changed = line is not None
            if changed:
                parse(line, st)
            now = time.time()
            if changed or now - last_paint >= 0.5:
                sys.stdout.write('\033[H' + render(st, frame) + '\033[0J')
                sys.stdout.flush()
                last_paint = now; frame += 1
            if st['done'] and line is None:
                break
            time.sleep(0.1)
    finally:
        sys.stdout.write(ALT_OFF)
        sys.stdout.flush()


def run_training(args):
    st = new_state()
    here = os.path.dirname(os.path.abspath(__file__))
    proc = subprocess.Popen([sys.executable, '-u', 'train.py'] + args, cwd=here,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    q = collections.deque()
    lock = threading.Lock()

    def reader():
        for ln in proc.stdout:
            with lock: q.append(ln)
        with lock: q.append(None)  # EOF sentinel
    threading.Thread(target=reader, daemon=True).start()

    def get_line():
        with lock:
            return q.popleft() if q else (None if proc.poll() is None else False)
    # get_line: 行/None(待ち)/False(終了) を返す → loop 用に薄く包む
    eof = [False]

    def gl():
        v = get_line()
        if v is False:
            eof[0] = True; st['done'] = st['done'] or True; return None
        return v
    interrupted = False
    try:
        loop(gl, st)
    except KeyboardInterrupt:
        interrupted = True
    if interrupted:
        try: proc.terminate()
        except Exception: pass
    proc.wait()
    ev = st['last_eval']
    tag = 'を中断（学習も停止）' if interrupted else '完了'
    sys.stdout.write(f"{C['yellow']}■ 学習{tag}{C['reset']}  ラウンド{st['rnd']} 総対局{st['games']} "
                     f"最終eval={ev if ev is not None else '--'}  （ckptは --out=既定 ckpt/ に保存済み）\n")
    sys.stdout.flush()


def demo():
    st = new_state()
    canned = [
        "device=cpu N=7 sims=48 workers=30 lr=0.001 t-frac=0.3 hours=1.0",
        "endgame solver: cells<=9 budget=60000 nodes",
        "teacher samples = 8967",
        "  warm ep4: ploss=3.587 vloss=0.127",
        "  warm ep6: ploss=3.215 vloss=0.086",
        "  [eval warm後] 網-MCTS vs 捕獲貪欲 勝率 = 0.00",
        "round 1 t=0.7m tf=0.29 games=60 buf=774 ploss=2.632 vloss=0.100",
        "round 2 t=1.9m tf=0.28 games=60 buf=1538 ploss=2.351 vloss=0.084",
        "  [eval r2] 網-MCTS vs 捕獲貪欲 勝率 = 0.08",
        "round 3 t=3.2m tf=0.26 games=60 buf=2280 ploss=2.182 vloss=0.089",
        "round 4 t=4.3m tf=0.25 games=60 buf=3056 ploss=2.061 vloss=0.082",
        "  [eval r4] 網-MCTS vs 捕獲貪欲 勝率 = 0.25",
        "round 5 t=5.5m tf=0.23 games=60 buf=3800 ploss=1.940 vloss=0.079",
        "  [eval r5] 網-MCTS vs 捕獲貪欲 勝率 = 0.50",
        "done -> ckpt/net_final.pt",
    ]
    it = iter(canned); pending = [True]

    def gl():
        if pending[0]:
            nx = next(it, '__END__')
            if nx == '__END__':
                pending[0] = False; return None
            # デモは1行を数フレーム見せる
            for _ in range(6):
                sys.stdout.write('\033[H' + render_after(st) + '\033[J'); sys.stdout.flush(); time.sleep(0.12)
            return nx
        return None

    def render_after(s):
        return render(s, int(time.time() * 8) % len(SPIN))
    sys.stdout.write(ALT_ON)
    try:
        while True:
            ln = gl()
            if ln is not None:
                parse(ln, st)
            sys.stdout.write('\033[H' + render(st, int(time.time() * 8) % 99) + '\033[J'); sys.stdout.flush()
            time.sleep(0.12)
            if not pending[0] and st['done']:
                sys.stdout.write('\033[H' + render(st, 0) + '\033[J'); time.sleep(1.2); break
    finally:
        sys.stdout.write(ALT_OFF + '\n'); sys.stdout.flush()


def selftest():
    st = new_state()
    for ln in ["device=cpu N=7 sims=48 workers=30 lr=0.001 t-frac=0.3 hours=1.0",
               "endgame solver: cells<=9 budget=60000 nodes",
               "teacher samples = 8967",
               "  warm ep6: ploss=3.215 vloss=0.086",
               "round 4 t=4.3m tf=0.25 games=60 buf=3056 ploss=2.061 vloss=0.082",
               "  [eval r4] 網-MCTS vs 捕獲貪欲 勝率 = 0.25",
               "done -> ckpt/net_final.pt"]:
        parse(ln, st)
    ok = (st['N'] == 7 and st['workers'] == 30 and st['rnd'] == 4 and st['games'] == 60
          and st['last_eval'] == 0.25 and st['done'] and st['solver'] and len(st['ploss']) == 2)
    txt = render(st, 0)  # 描画も例外なく通るか
    print("selftest:", "OK" if ok and txt else "FAIL", "| eval=", st['last_eval'], "rnd=", st['rnd'], "games=", st['games'])


if __name__ == '__main__':
    a = sys.argv[1:]
    if a and a[0] == '--selftest':
        selftest()
    elif a and a[0] == '--demo':
        demo()
    else:
        run_training(a)
