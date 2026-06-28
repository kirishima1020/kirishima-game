"""PUCT MCTS（AlphaZero型）。2人戦・ゼロ和。
evaluate(state) -> (priors: {move_id: prob over legal}, value in [-1,1]  ※state.turn 視点)
を差し替え可能にして、網でもスタブでも回せる。
各ノードの W はそのノードの手番視点で積む。選択時は親視点に符号を合わせる（スキップ対応）。
"""
import math
import engine as E


class Node:
    __slots__ = ('turn', 'P', 'N', 'W', 'children', 'expanded')
    def __init__(self, turn, prior):
        self.turn = turn      # このノードで打つ手番（0=終局）。子は初回選択時に確定。
        self.P = prior
        self.N = 0
        self.W = 0.0
        self.children = {}
        self.expanded = False
    def Q(self):
        return self.W / self.N if self.N > 0 else 0.0


def _terminal_value(s, who):
    w = E.winner(s)
    if w == 0: return 0.0
    return 1.0 if w == who else -1.0


def _select(node, c_puct):
    sumN = sum(ch.N for ch in node.children.values())
    sq = math.sqrt(sumN) if sumN > 0 else 1.0
    best, best_u, best_mid = None, -1e30, -1
    for mid, ch in node.children.items():
        q = ch.Q() if ch.turn == node.turn else -ch.Q()   # 親(node)視点に揃える
        u = q + c_puct * ch.P * sq / (1 + ch.N)
        if u > best_u:
            best_u = u; best = ch; best_mid = mid
    return best_mid, best


def search(root_state, evaluate, sims, c_puct=1.5, dirichlet=0.0, rng=None):
    root = Node(root_state.turn, 1.0)
    rp, _rv = evaluate(root_state)
    for mid, p in rp.items():
        root.children[mid] = Node(0, p)
    root.expanded = True
    if dirichlet > 0 and rng is not None and root.children:
        ks = list(root.children.keys())
        noise = _dirichlet(len(ks), dirichlet, rng)
        for k, nz in zip(ks, noise):
            root.children[k].P = 0.75 * root.children[k].P + 0.25 * nz

    for _ in range(sims):
        s = root_state.clone()
        node = root
        path = [node]
        while node.expanded and node.children:
            mid, child = _select(node, c_puct)
            E.play(s, mid, s.turn)
            child.turn = s.turn
            node = child
            path.append(node)
            if s.turn == 0:
                break
        if s.turn == 0:
            leaf_turn = path[-2].turn if len(path) >= 2 else root.turn
            v = _terminal_value(s, leaf_turn)
        else:
            priors, v = evaluate(s)
            for mid, p in priors.items():
                node.children[mid] = Node(0, p)
            node.expanded = True
            leaf_turn = s.turn
        for nd in path:
            nd.N += 1
            nd.W += v if (nd.turn == leaf_turn) else -v

    return {mid: ch.N for mid, ch in root.children.items()}


def _dirichlet(k, alpha, rng):
    xs = [rng.gammavariate(alpha, 1.0) for _ in range(k)]
    t = sum(xs) or 1.0
    return [x / t for x in xs]


def pick_move(visits, temperature=1.0, rng=None):
    """temp<=0 で最多訪問、>0 で確率的（訪問^(1/temp)）。"""
    if not visits: return -1
    if temperature <= 1e-6 or rng is None:
        return max(visits.items(), key=lambda kv: kv[1])[0]
    ks = list(visits.keys())
    ws = [visits[k] ** (1.0 / temperature) for k in ks]
    t = sum(ws) or 1.0
    r = rng.random() * t
    acc = 0.0
    for k, w in zip(ks, ws):
        acc += w
        if r <= acc: return k
    return ks[-1]
