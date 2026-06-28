"""mcts.py のローカル検証。スタブ評価器（価値=得点差）のMCTS vs 乱択。
探索の向きが正しければ勝ち越す。負け越すなら符号が逆。"""
import random, engine as E, mcts as M

def stub(s):
    lm = E.legal_moves(s, s.turn)
    p = {mid: 1.0 / len(lm) for mid in lm} if lm else {}
    me = s.turn; opp = 2 if me == 1 else 1
    v = (s.score[me] - s.score[opp]) / (s.M * s.M)
    return p, max(-1.0, min(1.0, v))

def random_move(s, rng):
    lm = E.legal_moves(s, s.turn)
    return lm[rng.randrange(len(lm))] if lm else -1

def game(mcts_seat, seed, sims):
    rng = random.Random(seed); s = E.make_game(7, 2)
    while s.turn != 0:
        if s.turn == mcts_seat:
            mv = M.pick_move(M.search(s, stub, sims, rng=rng), 0.0, rng)
        else:
            mv = random_move(s, rng)
        if mv < 0: break
        E.play(s, mv, s.turn)
        if s.moves > 500: break
    return s.score[1], s.score[2]

w = t = 0; G = 8; SIMS = 80
for g in range(G):
    seat = (g % 2) + 1
    a, b = game(seat, 100 + g * 13, SIMS)
    me = a if seat == 1 else b; o = b if seat == 1 else a
    res = 'win' if me > o else ('lose' if me < o else 'tie')
    if me > o: w += 1
    elif me == o: t += 1
    print(f"  g{g+1} mcts=P{seat} {a}/{b} {res}")
print(f"MCTS(stub sims={SIMS}) vs 乱択: {w}/{G} 勝 (引分{t})  -> 過半なら探索の向きOK")
