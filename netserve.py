"""ローカル網サーバ：play.html の「学習網と対局」に、学習網の手を返す。
同一オリジンにするため play.html / engine.js もこのサーバが配信する（CORS回避）。

  python3 netserve.py [ckpt=~/net_peak_r46.pt] [N=7] [port=8000]
  → ブラウザで  http://localhost:8000/play.html  を開く
  → 盤=7×7・人数=2 にして「学習網と対局」にチェック → 開始

網は N（既定7）専用・2人戦のみ。盤や人数が違うと手番のたびにエラーを返す。
"""
import sys, os, json, random
from http.server import HTTPServer, SimpleHTTPRequestHandler

os.chdir(os.path.dirname(os.path.abspath(__file__)))   # リポジトリ直下を配信ルートに
ckpt = os.path.expanduser(sys.argv[1]) if len(sys.argv) > 1 else os.path.expanduser('~/net_peak_r46.pt')
NETN = int(sys.argv[2]) if len(sys.argv) > 2 else 7
PORT = int(sys.argv[3]) if len(sys.argv) > 3 else 8000

sys.path.insert(0, 'az')
import torch, engine as E, model as MD, mcts as MC
dev = 'cuda' if torch.cuda.is_available() else 'cpu'
net = MD.Net(NETN).to(dev); net.load_state_dict(torch.load(ckpt, map_location=dev)); net.eval()
ev = MD.make_evaluator(net, dev)
rng = random.Random()
print(f'網 {ckpt} を {dev} で読み込み（N={NETN}・2人戦）。')
print(f'→ http://localhost:{PORT}/play.html を開き、盤7×7・人数2で「学習網と対局」にチェック。')


def pick(d):
    if int(d['P']) != 2: return {'error': '網は2人戦のみ。人数を2にして開始し直して。'}
    if int(d['N']) != NETN: return {'error': f'この網はN={NETN}専用。盤を{NETN}×{NETN}にして開始し直して。'}
    s = E.make_game(NETN, 2)
    s.H = list(d['H']); s.V = list(d['V']); s.cells = list(d['cells'])
    s.first = list(d['first']); s.score = list(d['score'])
    s.turn = int(d['turn']); s.moves = int(d.get('moves', 0))
    mv = MC.pick_move(MC.search(s, ev, int(d.get('sims', 400)), rng=rng), 0.0, rng)
    return {'move': int(mv)}


class Handler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/move': self.send_error(404); return
        n = int(self.headers.get('Content-Length', 0))
        try: out = pick(json.loads(self.rfile.read(n) or b'{}'))
        except Exception as e: out = {'error': repr(e)}
        body = json.dumps(out).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers(); self.wfile.write(body)

    def log_message(self, *a): pass


print('Ctrl-C で停止。')
HTTPServer(('127.0.0.1', PORT), Handler).serve_forever()
