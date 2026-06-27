'use strict';
// キリシマ N人エンジン（盤・合法手・閉領域塗り・UCT MCTS）。trends.js / selfplay.js / play.html が共有。
// 乱数は setSeed(seed) で固定可（既定 Math.random）。
// best(root, iters, smart): smart=true で捕獲認識ロールアウト（Stage 0）。既定 false＝従来の乱択。

let _rng = Math.random;
function setSeed(seed){
  let a = (seed >>> 0) || 1;
  _rng = function(){ a|=0; a=a+0x6D2B79F5|0; let t=Math.imul(a^a>>>15,1|a); t=t+Math.imul(t^t>>>7,61|t)^t; return ((t^t>>>14)>>>0)/4294967296; };
}

const HC=n=>n*(n-1), EC=n=>2*n*(n-1);

function makeGame(N,P){const M=N-1;return{N,P,M,H:new Int8Array(N*(N-1)),V:new Int8Array((N-1)*N),cells:new Int8Array(M*M),first:new Uint8Array(P+1),score:new Int32Array(P+1),turn:1,moves:0};}
function clone(s){return{N:s.N,P:s.P,M:s.M,H:s.H.slice(),V:s.V.slice(),cells:s.cells.slice(),first:s.first.slice(),score:s.score.slice(),turn:s.turn,moves:s.moves};}

let _conn=new Uint8Array(64),_q=new Int32Array(64),_buf=new Int32Array(256);
function ensure(N){const M=N-1;if(_conn.length<M*M){_conn=new Uint8Array(M*M);_q=new Int32Array(M*M);}if(_buf.length<EC(N))_buf=new Int32Array(EC(N));}

function vtx(s,ix,iy,p){const N=s.N,H=s.H,V=s.V;if(ix>0&&H[iy*(N-1)+ix-1]===p)return true;if(ix<N-1&&H[iy*(N-1)+ix]===p)return true;if(iy>0&&V[(iy-1)*N+ix]===p)return true;if(iy<N-1&&V[iy*N+ix]===p)return true;return false;}
function inside(s,isH,x,y){const M=s.M,c=s.cells;if(isH){if(y>=1&&y<M)return c[(y-1)*M+x]!==0&&c[y*M+x]!==0;return false;}else{if(x>=1&&x<M)return c[y*M+x-1]!==0&&c[y*M+x]!==0;return false;}}
function valid(s,id,p){const N=s.N,hc=HC(N);let isH,x,y;if(id<hc){isH=true;y=(id/(N-1))|0;x=id%(N-1);if(s.H[id]!==0)return false;}else{const v=id-hc;isH=false;y=(v/N)|0;x=v%N;if(s.V[v]!==0)return false;}if(inside(s,isH,x,y))return false;if(!s.first[p])return true;if(isH)return vtx(s,x,y,p)||vtx(s,x+1,y,p);return vtx(s,x,y,p)||vtx(s,x,y+1,p);}
function legal(s,p,buf){const E=EC(s.N);let n=0;for(let id=0;id<E;id++)if(valid(s,id,p))buf[n++]=id;return n;}
function hasMove(s,p){const E=EC(s.N);for(let id=0;id<E;id++)if(valid(s,id,p))return true;return false;}
function fill(s,p){const M=s.M,N=s.N,H=s.H,V=s.V,c=s.cells,conn=_conn,q=_q;for(let i=0;i<M*M;i++)conn[i]=0;let qt=0,qh=0;
  for(let y=0;y<M;y++)for(let x=0;x<M;x++){if(x!==0&&x!==M-1&&y!==0&&y!==M-1)continue;let o=false;if(x===0&&V[y*N]===0)o=true;else if(x===M-1&&V[y*N+x+1]===0)o=true;else if(y===0&&H[x]===0)o=true;else if(y===M-1&&H[(y+1)*(N-1)+x]===0)o=true;if(o&&!conn[y*M+x]){conn[y*M+x]=1;q[qt++]=y*M+x;}}
  while(qh<qt){const cc=q[qh++],cx=cc%M,cy=(cc/M)|0;
    if(cx+1<M&&!conn[cy*M+cx+1]&&V[cy*N+cx+1]===0){conn[cy*M+cx+1]=1;q[qt++]=cy*M+cx+1;}
    if(cx-1>=0&&!conn[cy*M+cx-1]&&V[cy*N+cx]===0){conn[cy*M+cx-1]=1;q[qt++]=cy*M+cx-1;}
    if(cy+1<M&&!conn[(cy+1)*M+cx]&&H[(cy+1)*(N-1)+cx]===0){conn[(cy+1)*M+cx]=1;q[qt++]=(cy+1)*M+cx;}
    if(cy-1>=0&&!conn[(cy-1)*M+cx]&&H[cy*(N-1)+cx]===0){conn[(cy-1)*M+cx]=1;q[qt++]=(cy-1)*M+cx;}}
  let g=0;for(let i=0;i<M*M;i++)if(c[i]===0&&!conn[i]){c[i]=p;g++;}return g;}

// 読み取り専用：現盤面で「未塗り かつ 外部非連結」のセル数（＝塗らずに数える）。
function countEnclosed(s){const M=s.M,N=s.N,H=s.H,V=s.V,c=s.cells,conn=_conn,q=_q;for(let i=0;i<M*M;i++)conn[i]=0;let qt=0,qh=0;
  for(let y=0;y<M;y++)for(let x=0;x<M;x++){if(x!==0&&x!==M-1&&y!==0&&y!==M-1)continue;let o=false;if(x===0&&V[y*N]===0)o=true;else if(x===M-1&&V[y*N+x+1]===0)o=true;else if(y===0&&H[x]===0)o=true;else if(y===M-1&&H[(y+1)*(N-1)+x]===0)o=true;if(o&&!conn[y*M+x]){conn[y*M+x]=1;q[qt++]=y*M+x;}}
  while(qh<qt){const cc=q[qh++],cx=cc%M,cy=(cc/M)|0;
    if(cx+1<M&&!conn[cy*M+cx+1]&&V[cy*N+cx+1]===0){conn[cy*M+cx+1]=1;q[qt++]=cy*M+cx+1;}
    if(cx-1>=0&&!conn[cy*M+cx-1]&&V[cy*N+cx]===0){conn[cy*M+cx-1]=1;q[qt++]=cy*M+cx-1;}
    if(cy+1<M&&!conn[(cy+1)*M+cx]&&H[(cy+1)*(N-1)+cx]===0){conn[(cy+1)*M+cx]=1;q[qt++]=(cy+1)*M+cx;}
    if(cy-1>=0&&!conn[(cy-1)*M+cx]&&H[cy*(N-1)+cx]===0){conn[(cy-1)*M+cx]=1;q[qt++]=(cy-1)*M+cx;}}
  let g=0;for(let i=0;i<M*M;i++)if(c[i]===0&&!conn[i])g++;return g;}
// 候補手id を置いたら何マス閉じるか（置く→数える→戻す。塗らない）。
function captureGain(s,id){const hc=HC(s.N);let isH,ei;if(id<hc){isH=true;ei=id;}else{isH=false;ei=id-hc;}if(isH)s.H[ei]=1;else s.V[ei]=1;const g=countEnclosed(s);if(isH)s.H[ei]=0;else s.V[ei]=0;return g;}

function advance(s){const P=s.P;for(let k=1;k<=P;k++){const np=((s.turn-1+k)%P)+1;if(hasMove(s,np)){s.turn=np;return;}}s.turn=0;}
function play(s,id,p){const hc=HC(s.N);if(id<hc)s.H[id]=p;else s.V[id-hc]=p;s.first[p]=1;const g=fill(s,p);s.score[p]+=g;s.moves++;advance(s);return g;}

const C=Math.SQRT2;
// smart=true: プレイアウト中、捕獲できる手があれば最大総取りを選ぶ（無ければ乱択）。
function rollout(s0,cells,smart){const s=clone(s0);while(s.turn!==0){const n=legal(s,s.turn,_buf);if(!n){advance(s);continue;}let mv;
    if(smart){const K=n<14?n:14;let bg=0,bid=-1;for(let i=0;i<K;i++){const id=_buf[(_rng()*n)|0];const g=captureGain(s,id);if(g>bg){bg=g;bid=id;}}mv=bg>0?bid:_buf[(_rng()*n)|0];}
    else mv=_buf[(_rng()*n)|0];
    play(s,mv,s.turn);}
  const r=new Float64Array(s.P+1);for(let i=1;i<=s.P;i++)r[i]=s.score[i]/cells;return r;}
function term(s,cells){const r=new Float64Array(s.P+1);for(let i=1;i<=s.P;i++)r[i]=s.score[i]/cells;return r;}
function node(s){const nd={s,m:-1,n:0,W:new Float64Array(s.P+1),c:[],u:[]};if(s.turn!==0){const k=legal(s,s.turn,_buf);for(let i=0;i<k;i++)nd.u.push(_buf[i]);}return nd;}
function sel(nd){const tm=nd.s.turn,ln=Math.log(nd.n+1);let b=null,bu=-1e9;for(const ch of nd.c){const u=ch.W[tm]/ch.n+C*Math.sqrt(ln/ch.n);if(u>bu){bu=u;b=ch;}}return b;}
function best(root,iters,smart){const P=root.P,cells=root.M*root.M;const rt=node(clone(root));for(let it=0;it<iters;it++){let nd=rt;const path=[nd];while(nd.u.length===0&&nd.c.length>0){nd=sel(nd);path.push(nd);}if(nd.u.length>0&&nd.s.turn!==0){const id=nd.u.pop();const ns=clone(nd.s);play(ns,id,nd.s.turn);const ch=node(ns);ch.m=id;nd.c.push(ch);path.push(ch);nd=ch;}const r=nd.s.turn===0?term(nd.s,cells):rollout(nd.s,cells,smart);for(const x of path){x.n++;for(let p=1;p<=P;p++)x.W[p]+=r[p];}}let bm=-1,bv=-1;for(const ch of rt.c)if(ch.n>bv){bv=ch.n;bm=ch.m;}return bm;}

// 辺id -> {type,x,y}（main.js / viewer の H[y][x]・V[y][x] 座標系）
function edgeXY(N,id){const hc=N*(N-1);if(id<hc)return{type:'H',x:id%(N-1),y:(id/(N-1))|0};const v=id-hc;return{type:'V',x:v%N,y:(v/N)|0};}

const __api={setSeed,HC,EC,makeGame,clone,ensure,legal,hasMove,fill,advance,play,best,edgeXY};
if(typeof module!=='undefined'&&module.exports) module.exports=__api;        // Node（selfplay/ladder/trends/probe/stage0）
else if(typeof globalThis!=='undefined') globalThis.KirishimaEngine=__api;   // ブラウザ（play.html）
