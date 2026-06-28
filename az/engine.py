"""キリシマ ルール（engine.js の移植）。AlphaZero 学習用。
ルール部は純Python（numpy不要）でJS版と一手一手一致させる。planes()のみ学習時にnumpyを使う。
"""

def HC(n): return n * (n - 1)
def EC(n): return 2 * n * (n - 1)


class State:
    __slots__ = ('N', 'P', 'M', 'H', 'V', 'cells', 'first', 'score', 'turn', 'moves')

    def __init__(self, N, P):
        self.N = N; self.P = P; self.M = N - 1
        self.H = [0] * (N * (N - 1))
        self.V = [0] * ((N - 1) * N)
        self.cells = [0] * ((N - 1) * (N - 1))
        self.first = [0] * (P + 1)
        self.score = [0] * (P + 1)
        self.turn = 1; self.moves = 0

    def clone(self):
        s = State.__new__(State)
        s.N = self.N; s.P = self.P; s.M = self.M
        s.H = self.H[:]; s.V = self.V[:]; s.cells = self.cells[:]
        s.first = self.first[:]; s.score = self.score[:]
        s.turn = self.turn; s.moves = self.moves
        return s


def make_game(N, P):
    return State(N, P)


def vtx(s, ix, iy, p):
    N = s.N; H = s.H; V = s.V
    if ix > 0 and H[iy * (N - 1) + ix - 1] == p: return True
    if ix < N - 1 and H[iy * (N - 1) + ix] == p: return True
    if iy > 0 and V[(iy - 1) * N + ix] == p: return True
    if iy < N - 1 and V[iy * N + ix] == p: return True
    return False


def inside(s, isH, x, y):
    M = s.M; c = s.cells
    if isH:
        if 1 <= y < M: return c[(y - 1) * M + x] != 0 and c[y * M + x] != 0
        return False
    else:
        if 1 <= x < M: return c[y * M + x - 1] != 0 and c[y * M + x] != 0
        return False


def valid(s, mid, p):
    N = s.N; hc = HC(N)
    if mid < hc:
        isH = True; y = mid // (N - 1); x = mid % (N - 1)
        if s.H[mid] != 0: return False
    else:
        v = mid - hc; isH = False; y = v // N; x = v % N
        if s.V[v] != 0: return False
    if inside(s, isH, x, y): return False
    if not s.first[p]: return True
    if isH: return vtx(s, x, y, p) or vtx(s, x + 1, y, p)
    return vtx(s, x, y, p) or vtx(s, x, y + 1, p)


def legal_moves(s, p):
    return [mid for mid in range(EC(s.N)) if valid(s, mid, p)]


def has_move(s, p):
    for mid in range(EC(s.N)):
        if valid(s, mid, p): return True
    return False


def fill(s, p):
    M = s.M; N = s.N; H = s.H; V = s.V; c = s.cells
    conn = [0] * (M * M); q = []
    for y in range(M):
        for x in range(M):
            if x not in (0, M - 1) and y not in (0, M - 1): continue
            o = False
            if x == 0 and V[y * N] == 0: o = True
            elif x == M - 1 and V[y * N + x + 1] == 0: o = True
            elif y == 0 and H[x] == 0: o = True
            elif y == M - 1 and H[(y + 1) * (N - 1) + x] == 0: o = True
            if o and not conn[y * M + x]:
                conn[y * M + x] = 1; q.append(y * M + x)
    qi = 0
    while qi < len(q):
        cc = q[qi]; qi += 1; cx = cc % M; cy = cc // M
        if cx + 1 < M and not conn[cy * M + cx + 1] and V[cy * N + cx + 1] == 0: conn[cy * M + cx + 1] = 1; q.append(cy * M + cx + 1)
        if cx - 1 >= 0 and not conn[cy * M + cx - 1] and V[cy * N + cx] == 0: conn[cy * M + cx - 1] = 1; q.append(cy * M + cx - 1)
        if cy + 1 < M and not conn[(cy + 1) * M + cx] and H[(cy + 1) * (N - 1) + cx] == 0: conn[(cy + 1) * M + cx] = 1; q.append((cy + 1) * M + cx)
        if cy - 1 >= 0 and not conn[(cy - 1) * M + cx] and H[cy * (N - 1) + cx] == 0: conn[(cy - 1) * M + cx] = 1; q.append((cy - 1) * M + cx)
    g = 0
    for i in range(M * M):
        if c[i] == 0 and not conn[i]:
            c[i] = p; g += 1
    return g


def advance(s):
    P = s.P
    for k in range(1, P + 1):
        nxt = ((s.turn - 1 + k) % P) + 1
        if has_move(s, nxt):
            s.turn = nxt; return
    s.turn = 0


def play(s, mid, p):
    hc = HC(s.N)
    if mid < hc: s.H[mid] = p
    else: s.V[mid - hc] = p
    s.first[p] = 1
    g = fill(s, p)
    s.score[p] += g
    s.moves += 1
    advance(s)
    return g


def winner(s):
    """2人戦の勝者: 1 / 2 / 0(引分)。"""
    if s.score[1] > s.score[2]: return 1
    if s.score[2] > s.score[1]: return 2
    return 0


def count_enclosed(s):
    """未塗り かつ 外部非連結のセル数（塗らずに数える）。捕獲評価用。"""
    M = s.M; N = s.N; H = s.H; V = s.V; c = s.cells
    conn = [0] * (M * M); q = []
    for y in range(M):
        for x in range(M):
            if x not in (0, M - 1) and y not in (0, M - 1): continue
            o = False
            if x == 0 and V[y * N] == 0: o = True
            elif x == M - 1 and V[y * N + x + 1] == 0: o = True
            elif y == 0 and H[x] == 0: o = True
            elif y == M - 1 and H[(y + 1) * (N - 1) + x] == 0: o = True
            if o and not conn[y * M + x]:
                conn[y * M + x] = 1; q.append(y * M + x)
    qi = 0
    while qi < len(q):
        cc = q[qi]; qi += 1; cx = cc % M; cy = cc // M
        if cx + 1 < M and not conn[cy * M + cx + 1] and V[cy * N + cx + 1] == 0: conn[cy * M + cx + 1] = 1; q.append(cy * M + cx + 1)
        if cx - 1 >= 0 and not conn[cy * M + cx - 1] and V[cy * N + cx] == 0: conn[cy * M + cx - 1] = 1; q.append(cy * M + cx - 1)
        if cy + 1 < M and not conn[(cy + 1) * M + cx] and H[(cy + 1) * (N - 1) + cx] == 0: conn[(cy + 1) * M + cx] = 1; q.append((cy + 1) * M + cx)
        if cy - 1 >= 0 and not conn[(cy - 1) * M + cx] and H[cy * (N - 1) + cx] == 0: conn[(cy - 1) * M + cx] = 1; q.append((cy - 1) * M + cx)
    return sum(1 for i in range(M * M) if c[i] == 0 and not conn[i])


def capture_gain(s, mid):
    """候補手 mid を置いたら何マス閉じるか（置く→数える→戻す）。"""
    hc = HC(s.N)
    if mid < hc:
        if s.H[mid] != 0: return 0
        s.H[mid] = 1; g = count_enclosed(s); s.H[mid] = 0
    else:
        v = mid - hc
        if s.V[v] != 0: return 0
        s.V[v] = 1; g = count_enclosed(s); s.V[v] = 0
    return g


# ---- 学習用：盤を N×N の多チャンネル平面に符号化（手番=me 視点の正準形）----
def planes(s):
    import numpy as np
    N = s.N; M = s.M; me = s.turn; opp = 2 if me == 1 else 1
    P = np.zeros((7, N, N), dtype=np.float32)
    # cells (M×M)
    for y in range(M):
        for x in range(M):
            c = s.cells[y * M + x]
            if c == me: P[0, y, x] = 1
            elif c == opp: P[1, y, x] = 1
            else: P[2, y, x] = 1
    # H edges  H[y*(N-1)+x], y:0..N-1, x:0..N-2
    for y in range(N):
        for x in range(N - 1):
            h = s.H[y * (N - 1) + x]
            if h == me: P[3, y, x] = 1
            elif h == opp: P[4, y, x] = 1
    # V edges  V[y*N+x], y:0..N-2, x:0..N-1
    for y in range(N - 1):
        for x in range(N):
            v = s.V[y * N + x]
            if v == me: P[5, y, x] = 1
            elif v == opp: P[6, y, x] = 1
    return P
