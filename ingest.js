'use strict';
// キリシマ 対局ログ受信サーバ。VPSで起動して、静的サイト(GitHub Pages)から
// POSTされた各対局JSONを「1行1局」のNDJSONに追記する。依存なし(Node標準のみ)。
// 使い方: node ingest.js [port=8788] [outfile=games.ndjson]
//   GET  /        -> 健康確認＋現在の蓄積局数
//   POST /ingest  -> 対局JSONを1行追記

const http = require('http'), fs = require('fs'), path = require('path');
const PORT = +process.argv[2] || 8788;
const OUT  = path.resolve(process.argv[3] || 'games.ndjson');

function send(res, code, obj){
  res.writeHead(code, {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'POST,GET,OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
  });
  res.end(JSON.stringify(obj));
}

const server = http.createServer((req, res) => {
  if(req.method === 'OPTIONS') return send(res, 204, {});
  if(req.method === 'GET'){
    let count = 0; try{ count = fs.readFileSync(OUT,'utf8').split('\n').filter(Boolean).length; }catch(e){}
    return send(res, 200, { ok:true, count, out:OUT });
  }
  if(req.method === 'POST'){
    let body = '', tooBig = false;
    req.on('data', c => { body += c; if(body.length > 4e6){ tooBig = true; req.destroy(); } });
    req.on('end', () => {
      if(tooBig) return send(res, 413, { ok:false, error:'too large' });
      let log; try{ log = JSON.parse(body); }catch(e){ return send(res, 400, { ok:false, error:'bad json' }); }
      if(!log || !log.meta || !Array.isArray(log.moves)) return send(res, 400, { ok:false, error:'not a game log' });
      const rec = { recvAt:new Date().toISOString(), ip:(req.headers['x-forwarded-for']||req.socket.remoteAddress||'').split(',')[0].trim(), ...log };
      try{ fs.appendFileSync(OUT, JSON.stringify(rec) + '\n'); }catch(e){ return send(res, 500, { ok:false, error:'write failed' }); }
      return send(res, 200, { ok:true });
    });
    return;
  }
  send(res, 405, { ok:false, error:'method' });
});

server.listen(PORT, () => console.log(`kirishima ingest on :${PORT} -> ${OUT}`));
