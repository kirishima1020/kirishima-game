"""進捗評価用のベースライン着手。捕獲貪欲（1手先で最大総取りを取る・無ければ乱択）。
ver2+ より弱いが安く、網が"本物の戦略"を学べてるかの目安になる。"""
import engine as E


def greedy_move(s, rng):
    lm = E.legal_moves(s, s.turn)
    if not lm: return -1
    bg = 0; bid = -1
    for mid in lm:
        g = E.capture_gain(s, mid)
        if g > bg: bg = g; bid = mid
    return bid if bg > 0 else lm[rng.randrange(len(lm))]
