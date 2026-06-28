"""キリシマ 2人厳密終盤ソルバ（lab/solve.js の solveStrong の移植）。
margin = score[1]-score[2] を双方最善で読み切る。置換表つき。将来margin は現在スコアに依らず
盤面だけで決まるので、手順違いの同一局面を共有して指数を潰す。
学習では endgame_value() を使い、終盤に入った自己対局を「厳密な勝敗」で打ち切る。

自己検証:  python solve.py   （N=3 空盤=-2、PV再生一致、JSダンプとの突合）
"""
import engine as E


class BudgetError(Exception):
    pass


def _key(s):
    # 盤面だけ（H,V,cells,first,turn）。scoreは将来marginに無関係なので入れない。
    return (s.turn, tuple(s.H), tuple(s.V), tuple(s.cells), tuple(s.first))


def solve_strong(state, max_nodes=float('inf')):
    if state.P != 2:
        raise ValueError('2人戦のみ')
    TT = {}
    nodes = [0]

    def fut(s):
        if s.turn == 0:
            return 0
        k = _key(s)
        v = TT.get(k)
        if v is not None:
            return v
        nodes[0] += 1
        if nodes[0] > max_nodes:
            raise BudgetError()
        moves = E.legal_moves(s, s.turn)
        if not moves:
            ns = s.clone(); E.advance(ns)
            v = 0 if ns.turn == s.turn else fut(ns)
            TT[k] = v; return v
        base = s.score[1] - s.score[2]
        maxing = (s.turn == 1)
        best = None
        for mid in moves:
            ns = s.clone(); E.play(ns, mid, s.turn)
            val = (ns.score[1] - ns.score[2] - base) + fut(ns)
            if best is None or (val > best if maxing else val < best):
                best = val
        TT[k] = best
        return best

    s = state.clone()
    moves = E.legal_moves(s, s.turn)
    base = s.score[1] - s.score[2]
    maxing = (s.turn == 1)
    best = None; move = -1
    for mid in moves:
        ns = s.clone(); E.play(ns, mid, s.turn)
        val = (ns.score[1] - ns.score[2] - base) + fut(ns)
        if move < 0 or (val > best if maxing else val < best):
            best = val; move = mid
    return {'margin': base + best, 'move': move, 'nodes': nodes[0], 'tt': len(TT)}


def empty_cells(s):
    return sum(1 for c in s.cells if c == 0)


def endgame_value(s, max_cells=10, max_nodes=5_000_000):
    """終盤なら (winner, margin) を厳密に返す。範囲外/予算超過は None。
    winner: 1 / 2 / 0(引分)。margin = score1-score2（双方最善）。"""
    if s.P != 2 or s.turn == 0:
        return None
    if empty_cells(s) > max_cells:
        return None
    try:
        r = solve_strong(s, max_nodes)
    except BudgetError:
        return None
    m = r['margin']
    w = 1 if m > 0 else (2 if m < 0 else 0)
    return (w, m)


def principal_variation(state):
    s = state.clone()
    while s.turn != 0:
        r = solve_strong(s)
        if r['move'] < 0:
            break
        E.play(s, r['move'], s.turn)
    return s.score[1] - s.score[2]


if __name__ == '__main__':
    import json, os
    g = E.make_game(3, 2)
    r = solve_strong(g)
    pv = principal_variation(g)
    print(f"検証1 N=3空盤: margin={r['margin']} (期待-2)  PV再生={pv}  "
          f"→ {'OK' if r['margin'] == -2 == pv else '不一致!!'}")

    # JS が吐いた終盤局面との突合（あれば）
    path = '/tmp/xpos.json'
    if os.path.exists(path):
        total = mis = 0
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                s = E.State(d['N'], 2)
                s.H = d['H']; s.V = d['V']; s.cells = d['cells']
                s.first = d['first']; s.score = d['score']; s.turn = d['turn']
                m = solve_strong(s)['margin']
                total += 1
                if m != d['margin']:
                    mis += 1
                    if mis <= 8:
                        print(f"  X JS={d['margin']} PY={m}")
        print(f"検証2 JS突合: {total}局面  食い違い {mis}  "
              f"→ {'全一致。言語をまたいで同じ答え。' if mis == 0 else '不一致あり!!'}")
    else:
        print("検証2: /tmp/xpos.json が無いのでスキップ（JS側ダンプ未生成）")
