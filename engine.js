'use strict';
// キリシマ N人エンジン（盤・合法手・閉領域塗り・UCT MCTS）。trends/selfplay/play.html 等が共有。
// 乱数は setSeed(seed) で固定可（既定 Math.random）。
// best(root, iters, smart, useValue):
//   smart=true    捕獲認識ロールアウト（Stage 0・既定の app AI）
//   useValue=true 学習価値を葉評価に（Stage 2・ロールアウト無し＝速い／2人戦のみ、それ以外は得点比に退避）

let _rng = Math.random;
function setSeed(seed){
  let a = (seed >>> 0) || 1;
  _rng = function(){ a|=0; a=a+0x6D2B79F5|0; let t=Math.imul(a^a>>>15,1|a); t=t+Math.imul(t^t>>>7,61|t)^t; return ((t^t>>>14)>>>0)/4294967296; };
}

const HC=n=>n*(n-1), EC=n=>2*n*(n-1);

function makeGame(N,P){const M=N-1;return{N,P,M,H:new Int8Array(N*(N-1)),V:new Int8Array((N-1)*N),cells:new Int8Array(M*M),first:new Uint8Array(P+1),score:new Int32Array(P+1),turn:1,moves:0};}
function clone(s){return{N:s.N,P:s.P,M:s.M,H:s.H.slice(),V:s.V.slice(),cells:s.cells.slice(),first:s.first.slice(),score:s.score.slice(),turn:s.turn,moves:s.moves};}

let _conn=new Uint8Array(64),_q=new Int32Array(64),_buf=new Int32Array(256),_vbuf=new Int32Array(256);
function ensure(N){const M=N-1;if(_conn.length<M*M){_conn=new Uint8Array(M*M);_q=new Int32Array(M*M);}if(_buf.length<EC(N)){_buf=new Int32Array(EC(N));_vbuf=new Int32Array(EC(N));}}

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

// 読み取り専用：未塗り かつ 外部非連結のセル数（塗らずに数える）。
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

// 領地推定：空きセルを開いた共有辺で連結成分に分け、境界壁を多く持つ側へその成分を割り当てる。
function territory(s){const M=s.M,N=s.N,H=s.H,V=s.V,c=s.cells,P=s.P;const comp=new Int32Array(M*M).fill(-1),terr=new Float64Array(P+1),q=[];
  for(let start=0;start<M*M;start++){if(c[start]!==0||comp[start]>=0)continue;comp[start]=0;q.length=0;q.push(start);let sz=0;const owner=new Float64Array(P+1);
    while(q.length){const cc=q.pop(),cx=cc%M,cy=(cc/M)|0;sz++;let e;
      e=V[cy*N+cx+1];if(e!==0)owner[e]++;else if(cx+1<M){const nb=cy*M+cx+1;if(c[nb]===0&&comp[nb]<0){comp[nb]=0;q.push(nb);}}
      e=V[cy*N+cx];  if(e!==0)owner[e]++;else if(cx-1>=0){const nb=cy*M+cx-1;if(c[nb]===0&&comp[nb]<0){comp[nb]=0;q.push(nb);}}
      e=H[(cy+1)*(N-1)+cx];if(e!==0)owner[e]++;else if(cy+1<M){const nb=(cy+1)*M+cx;if(c[nb]===0&&comp[nb]<0){comp[nb]=0;q.push(nb);}}
      e=H[cy*(N-1)+cx];    if(e!==0)owner[e]++;else if(cy-1>=0){const nb=(cy-1)*M+cx;if(c[nb]===0&&comp[nb]<0){comp[nb]=0;q.push(nb);}}}
    let mo=0,mp=0;for(let p=1;p<=P;p++)if(owner[p]>mo){mo=owner[p];mp=p;}if(mp>0)terr[mp]+=sz;}
  return terr;}

// 学習済み価値（ロジスティック回帰・目標=勝敗 P(win)）。「過半を取れば勝ち」を焼くため share でなく勝敗を学習。
// [bias,自score,相手score,自前線,相手前線,自領地,相手領地,進行率]。2人戦。
const VW=[0.210148,2.926297,-2.649967,0.51957,-0.541604,0.744403,-1.253029,0.483282];
function valueEval(s,cells){const r=new Float64Array(s.P+1);
  if(s.P!==2){let tot=0;for(let i=1;i<=s.P;i++)tot+=s.score[i];tot=tot||1;for(let i=1;i<=s.P;i++)r[i]=s.score[i]/tot;return r;}
  const E=EC(s.N),tr=territory(s),prog=s.moves/(2*cells);
  for(let i=1;i<=2;i++){const j=i===1?2:1;
    const v=VW[0]+VW[1]*(s.score[i]/cells)+VW[2]*(s.score[j]/cells)+VW[3]*(legal(s,i,_vbuf)/E)+VW[4]*(legal(s,j,_vbuf)/E)+VW[5]*(tr[i]/cells)+VW[6]*(tr[j]/cells)+VW[7]*prog;
    r[i]=1/(1+Math.exp(-v));}   // sigmoid → P(win)
  return r;}

function advance(s){const P=s.P;for(let k=1;k<=P;k++){const np=((s.turn-1+k)%P)+1;if(hasMove(s,np)){s.turn=np;return;}}s.turn=0;}
function play(s,id,p){const hc=HC(s.N);if(id<hc)s.H[id]=p;else s.V[id-hc]=p;s.first[p]=1;const g=fill(s,p);s.score[p]+=g;s.moves++;advance(s);return g;}

const C=Math.SQRT2;
// 終局のスコアを「勝敗」ベクトルに（勝者=1・同点は分配・敗者=0）。「過半取れば勝ち」を探索の目標に。
function winVec(s){const r=new Float64Array(s.P+1);let mx=-1,mc=0;for(let i=1;i<=s.P;i++){if(s.score[i]>mx){mx=s.score[i];mc=1;}else if(s.score[i]===mx)mc++;}for(let i=1;i<=s.P;i++)r[i]=s.score[i]===mx?1/mc:0;return r;}
// smart=true: プレイアウト中、捕獲できる手があれば（サンプルから）最大総取りを選ぶ。返り値は勝敗。
function rollout(s0,cells,smart){const s=clone(s0);while(s.turn!==0){const n=legal(s,s.turn,_buf);if(!n){advance(s);continue;}let mv;
    if(smart){const K=n<14?n:14;let bg=0,bid=-1;for(let i=0;i<K;i++){const id=_buf[(_rng()*n)|0];const g=captureGain(s,id);if(g>bg){bg=g;bid=id;}}mv=bg>0?bid:_buf[(_rng()*n)|0];}
    else mv=_buf[(_rng()*n)|0];
    play(s,mv,s.turn);}
  return winVec(s);}
function term(s,cells){return winVec(s);}
function node(s){const nd={s,m:-1,n:0,W:new Float64Array(s.P+1),c:[],u:[]};if(s.turn!==0){const k=legal(s,s.turn,_buf);for(let i=0;i<k;i++)nd.u.push(_buf[i]);}return nd;}
function sel(nd){const tm=nd.s.turn,ln=Math.log(nd.n+1);let b=null,bu=-1e9;for(const ch of nd.c){const u=ch.W[tm]/ch.n+C*Math.sqrt(ln/ch.n);if(u>bu){bu=u;b=ch;}}return b;}
function best(root,iters,smart,useValue){const P=root.P,cells=root.M*root.M;const rt=node(clone(root));for(let it=0;it<iters;it++){let nd=rt;const path=[nd];while(nd.u.length===0&&nd.c.length>0){nd=sel(nd);path.push(nd);}if(nd.u.length>0&&nd.s.turn!==0){const id=nd.u.pop();const ns=clone(nd.s);play(ns,id,nd.s.turn);const ch=node(ns);ch.m=id;nd.c.push(ch);path.push(ch);nd=ch;}const r=nd.s.turn===0?term(nd.s,cells):(useValue?valueEval(nd.s,cells):rollout(nd.s,cells,smart));for(const x of path){x.n++;for(let p=1;p<=P;p++)x.W[p]+=r[p];}}
  let bv=-1;for(const ch of rt.c)if(ch.n>bv)bv=ch.n;const top=rt.c.filter(ch=>ch.n>=0.9*bv);return top.length?top[(_rng()*top.length)|0].m:-1;}  // 上位手から揺らぎ（決定的すぎ＝読まれ対策）

// 辺id -> {type,x,y}（main.js / viewer の H[y][x]・V[y][x] 座標系）
function edgeXY(N,id){const hc=N*(N-1);if(id<hc)return{type:'H',x:id%(N-1),y:(id/(N-1))|0};const v=id-hc;return{type:'V',x:v%N,y:(v/N)|0};}

const __api={setSeed,HC,EC,makeGame,clone,ensure,legal,hasMove,fill,advance,play,best,edgeXY,territory};
if(typeof module!=='undefined'&&module.exports) module.exports=__api;        // Node
else if(typeof globalThis!=='undefined') globalThis.KirishimaEngine=__api;   // ブラウザ（play.html）
