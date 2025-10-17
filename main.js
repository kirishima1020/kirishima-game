/* キリシマ ローカル2人対戦（Canvas実装）
   - 斜め線なし
   - 最初の1手のみ任意、以降は自分の線と同じ格子点を共有する辺のみ
   - 閉じ領域は即塗り確定（塗替え不可）
   - パスなし。現手番が一切打てない場合は終了
*/

(() => {
  const canvas = document.getElementById('board');
  const ctx = canvas.getContext('2d');
  const restartBtn = document.getElementById('restartBtn');
  const gridSizeSelect = document.getElementById('gridSizeSelect');
  const turnInfo = document.getElementById('turnInfo');
  const scoreInfo = document.getElementById('scoreInfo');

  // 見た目設定
  const COLORS = {
    bg: '#0f1115',
    grid: '#8b949e',
    p1: '#3da5ff',
    p2: '#ff5d69',
    cellAlpha: 0.18,
    hlAlpha: 0.25,
    line: '#c9d1d9',
  };

  // 盤面ステート
  let N = parseInt(gridSizeSelect.value, 10); // 格子点数（例：9） => セル数は (N-1)*(N-1)
  let cellCount; // (N-1)
  let spacing;   // マスのピクセル
  let margin;    // 余白
  let radius;    // 格子点の半径
  let hoverEdge = null;

  // 線配列（0:未使用, 1:P1, 2:P2）
  // H: horizontalLines[y][x] (y: 0..N-1, x: 0..N-2)
  // V: verticalLines[y][x]   (y: 0..N-2, x: 0..N-1)
  let H, V;

  // セル塗り配列（0:未塗り, 1:P1, 2:P2）
  // cells[y][x] (y:0..N-2, x:0..N-2)
  let cells;

  // 各プレイヤーの最初の手が済んだか
  let firstPlaced = [false, false, false]; // index: 1|2

  // 現在手番（1 or 2）
  let turn = 1;

  // スコア
  let score = [0, 0, 0];

  // ゲーム終了フラグ
  let gameOver = false;

  function initBoard() {
    const size = Math.min(canvas.width, canvas.height);
    margin = 36;
    spacing = (size - margin * 2) / (N - 1);
    radius = Math.max(2, Math.min(4, Math.floor(spacing * 0.06)));
    cellCount = N - 1;

    H = Array.from({ length: N }, () => Array(N - 1).fill(0));
    V = Array.from({ length: N - 1 }, () => Array(N).fill(0));
    cells = Array.from({ length: N - 1 }, () => Array(N - 1).fill(0));

    firstPlaced = [false, false, false];
    turn = 1;
    score = [0, 0, 0];
    gameOver = false;
    hoverEdge = null;

    updateStatus();
    draw();
  }

  function updateStatus(msg = '') {
    turnInfo.textContent = gameOver
      ? 'ゲーム終了'
      : `手番: ${turn === 1 ? 'P1' : 'P2'}`;
    scoreInfo.textContent = `P1: ${score[1]}　|　P2: ${score[2]}${msg ? '　' + msg : ''}`;
  }

  function gridToXY(ix, iy) {
    return [margin + ix * spacing, margin + iy * spacing];
  }

  function drawGrid() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = COLORS.bg;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // セル塗り（下地）
    for (let y = 0; y < cellCount; y++) {
      for (let x = 0; x < cellCount; x++) {
        if (cells[y][x] !== 0) {
          const [x0, y0] = gridToXY(x, y);
          ctx.fillStyle = (cells[y][x] === 1 ? COLORS.p1 : COLORS.p2) + Math.floor(COLORS.cellAlpha * 255).toString(16).padStart(2, '0');
          // 上の色式は16進透明度付きの意図だが、Canvasは別指定が自然
          ctx.fillStyle = cells[y][x] === 1 ? `rgba(61,165,255,${COLORS.cellAlpha})` : `rgba(255,93,105,${COLORS.cellAlpha})`;
          ctx.fillRect(x0, y0, spacing, spacing);
        }
      }
    }

    // 格子線
    ctx.lineWidth = 1;
    ctx.strokeStyle = COLORS.grid;
    ctx.beginPath();
    for (let i = 0; i < N; i++) {
      // 横線
      const [x0, y] = gridToXY(0, i);
      const [x1, _] = gridToXY(N - 1, i);
      ctx.moveTo(x0, y);
      ctx.lineTo(x1, y);
      // 縦線
      const [xx, y0] = gridToXY(i, 0);
      const [__, y1] = gridToXY(i, N - 1);
      ctx.moveTo(xx, y0);
      ctx.lineTo(xx, y1);
    }
    ctx.stroke();

    // 置かれた線（太く）
    ctx.lineWidth = 4;
    ctx.lineCap = 'round';
    ctx.strokeStyle = COLORS.line;

    // 水平
    for (let y = 0; y < N; y++) {
      for (let x = 0; x < N - 1; x++) {
        const owner = H[y][x];
        if (owner !== 0) {
          const [x0, yy] = gridToXY(x, y);
          const [x1, _] = gridToXY(x + 1, y);
          ctx.strokeStyle = owner === 1 ? COLORS.p1 : COLORS.p2;
          ctx.beginPath();
          ctx.moveTo(x0, yy);
          ctx.lineTo(x1, yy);
          ctx.stroke();
        }
      }
    }

    // 垂直
    for (let y = 0; y < N - 1; y++) {
      for (let x = 0; x < N; x++) {
        const owner = V[y][x];
        if (owner !== 0) {
          const [xx, y0] = gridToXY(x, y);
          const [_, y1] = gridToXY(x, y + 1);
          ctx.strokeStyle = owner === 1 ? COLORS.p1 : COLORS.p2;
          ctx.beginPath();
          ctx.moveTo(xx, y0);
          ctx.lineTo(xx, y1);
          ctx.stroke();
        }
      }
    }

    // ホバー中の候補線
    if (hoverEdge && !gameOver) {
      ctx.save();
      ctx.globalAlpha = COLORS.hlAlpha;
      ctx.lineWidth = 10;
      ctx.strokeStyle = turn === 1 ? COLORS.p1 : COLORS.p2;

      if (hoverEdge.type === 'H') {
        const [x0, y0] = gridToXY(hoverEdge.x, hoverEdge.y);
        const [x1, _] = gridToXY(hoverEdge.x + 1, hoverEdge.y);
        ctx.beginPath();
        ctx.moveTo(x0, y0);
        ctx.lineTo(x1, y0);
        ctx.stroke();
      } else {
        const [x0, y0] = gridToXY(hoverEdge.x, hoverEdge.y);
        const [_, y1] = gridToXY(hoverEdge.x, hoverEdge.y + 1);
        ctx.beginPath();
        ctx.moveTo(x0, y0);
        ctx.lineTo(x0, y1);
        ctx.stroke();
      }
      ctx.restore();
    }

    // 格子点
    ctx.fillStyle = '#cdd3d8';
    for (let y = 0; y < N; y++) {
      for (let x = 0; x < N; x++) {
        const [gx, gy] = gridToXY(x, y);
        ctx.beginPath();
        ctx.arc(gx, gy, radius, 0, Math.PI * 2);
        ctx.fill();
      }
    }
  }

  function draw() {
    drawGrid();
  }

  // クリック位置から最も近い未使用エッジを拾う
  function pickEdge(mx, my) {
    // Canvas座標 -> 盤面相対
    // 候補は「水平/垂直の各エッジの中心線」への距離で選ぶ
    let best = null;
    let bestDist = Infinity;

    const threshold = spacing * 0.25; // これ以内なら選択可

    // 水平
    for (let y = 0; y < N; y++) {
      for (let x = 0; x < N - 1; x++) {
        if (H[y][x] !== 0) continue; // 埋まってる
        const [x0, yy] = gridToXY(x, y);
        const [x1, _] = gridToXY(x + 1, y);
        // 点と線分距離
        const d = pointSegDist(mx, my, x0, yy, x1, yy);
        if (d < bestDist) {
          bestDist = d;
          best = { type: 'H', x, y };
        }
      }
    }

    // 垂直
    for (let y = 0; y < N - 1; y++) {
      for (let x = 0; x < N; x++) {
        if (V[y][x] !== 0) continue;
        const [xx, y0] = gridToXY(x, y);
        const [_, y1] = gridToXY(x, y + 1);
        const d = pointSegDist(mx, my, xx, y0, xx, y1);
        if (d < bestDist) {
          bestDist = d;
          best = { type: 'V', x, y };
        }
      }
    }

    if (best && bestDist <= threshold) return best;
    return null;
  }

  function pointSegDist(px, py, x0, y0, x1, y1) {
    const vx = x1 - x0, vy = y1 - y0;
    const wx = px - x0, wy = py - y0;
    const c1 = vx * wx + vy * wy;
    if (c1 <= 0) return Math.hypot(px - x0, py - y0);
    const c2 = vx * vx + vy * vy;
    if (c2 <= c1) return Math.hypot(px - x1, py - y1);
    const b = c1 / c2;
    const bx = x0 + b * vx, by = y0 + b * vy;
    return Math.hypot(px - bx, py - by);
  }

  // このエッジが「自分の既存線と同じ格子点を共有する」条件を満たすか
  function isEdgeExtensionValid(edge, player) {
    // 最初の1手は無条件OK
    if (!firstPlaced[player]) return true;

    // エッジの両端の格子点を算出
    let endpoints;
    if (edge.type === 'H') {
      endpoints = [
        { x: edge.x,     y: edge.y },
        { x: edge.x + 1, y: edge.y }
      ];
    } else {
      endpoints = [
        { x: edge.x, y: edge.y     },
        { x: edge.x, y: edge.y + 1 }
      ];
    }
    // どちらかの格子点に、プレイヤーの線が接続していればOK
    return endpoints.some(p => vertexHasPlayerLine(p.x, p.y, player));
  }

  function vertexHasPlayerLine(ix, iy, player) {
    // その格子点に接する4本の可能な辺のうち、playerの線があるか
    // 左水平
    if (ix > 0 && H[iy][ix - 1] === player) return true;
    // 右水平
    if (ix < N - 1 && H[iy][ix] === player) return true;
    // 上垂直
    if (iy > 0 && V[iy - 1][ix] === player) return true;
    // 下垂直
    if (iy < N - 1 && V[iy][ix] === player) return true;
    return false;
  }

  // エッジを置く
  function placeEdge(edge, player) {
    if (edge.type === 'H') H[edge.y][edge.x] = player;
    else V[edge.y][edge.x] = player;
    firstPlaced[player] = true;

    // 塗り判定（閉領域探索）
    const newly = fillEnclosedIslands(player);
    if (newly > 0) {
      score[player] += newly;
    }
    updateStatus(newly > 0 ? `+${newly}` : '');
  }

  // 閉鎖領域を探索して塗る
  function fillEnclosedIslands(player) {
    // 「開いている辺（未使用）」を通れる通路として、Outside と連結なセルを除外し、
    // 残りの未塗りセルをすべて player 色で塗る。
    const h = cellCount, w = cellCount;
    const visited = Array.from({ length: h }, () => Array(w).fill(false));
    const connectedToOutside = Array.from({ length: h }, () => Array(w).fill(false));

    // 外部と繋がるセルをBFS
    const q = [];

    // 外部から入れる境界セルを列挙（四辺のいずれかが「未使用エッジ」なら外に繋がる）
    // ただし外からの開始点は、実質「境界セルで、外側に開口があるセル」
    for (let y = 0; y < h; y++) {
      for (let x of [0, w - 1]) {
        if (cellOpensToOutside(x, y)) {
          q.push([x, y]);
          connectedToOutside[y][x] = true;
        }
      }
    }
    for (let x = 0; x < w; x++) {
      for (let y of [0, h - 1]) {
        if (cellOpensToOutside(x, y)) {
          q.push([x, y]);
          connectedToOutside[y][x] = true;
        }
      }
    }

    const dirs = [
      [1, 0], [-1, 0], [0, 1], [0, -1]
    ];

    while (q.length) {
      const [cx, cy] = q.shift();
      for (const [dx, dy] of dirs) {
        const nx = cx + dx, ny = cy + dy;
        if (nx < 0 || ny < 0 || nx >= w || ny >= h) continue;
        if (connectedToOutside[ny][nx]) continue;
        // セル間の共有辺が開いていれば到達可能
        if (edgeBetweenCellsIsOpen(cx, cy, nx, ny)) {
          connectedToOutside[ny][nx] = true;
          q.push([nx, ny]);
        }
      }
    }

    // 「未塗り かつ 外部非連結」のセルを全塗り
    let gained = 0;
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        if (cells[y][x] === 0 && !connectedToOutside[y][x]) {
          cells[y][x] = player;
          gained += 1;
        }
      }
    }
    return gained;
  }

  function cellOpensToOutside(x, y) {
    // 境界側の辺が未使用なら外部に開いている
    // 左
    if (x === 0) {
      // セル左辺 = V[y][x] （y:0..N-2, x:0..N-1）
      if (V[y][x] === 0) return true;
    }
    // 右
    if (x === cellCount - 1) {
      if (V[y][x + 1] === 0) return true;
    }
    // 上
    if (y === 0) {
      if (H[y][x] === 0) return true;
    }
    // 下
    if (y === cellCount - 1) {
      if (H[y + 1][x] === 0) return true;
    }
    return false;
  }

  function edgeBetweenCellsIsOpen(x0, y0, x1, y1) {
    // 隣接セル間の共有辺が未使用か？
    if (x0 === x1) {
      // 縦に隣り合う -> 共有は水平エッジ
      const yMin = Math.min(y0, y1);
      // セル上辺: H[yMin+?]…セル座標に注意
      // セル(y,x)の上辺は H[y][x]
      // 下辺は H[y+1][x]
      // ここでは 共有辺 = max(y0, y1) の上辺 or minの下辺。まとめると H[yMin+1][x0]
      return H[yMin + 1][x0] === 0;
    } else if (y0 === y1) {
      // 横に隣り合う -> 共有は垂直エッジ
      const xMin = Math.min(x0, x1);
      // 共有辺 = V[y0][xMin+1]
      return V[y0][xMin + 1] === 0;
    }
    return false;
  }

  function hasAnyMoveFor(player) {
    // 未使用エッジのうち、ルールに適合するものが存在するか
    // 最初の1手なら未使用エッジがひとつでもあればOK
    if (!firstPlaced[player]) {
      for (let y = 0; y < N; y++) for (let x = 0; x < N - 1; x++) if (H[y][x] === 0) return true;
      for (let y = 0; y < N - 1; y++) for (let x = 0; x < N; x++) if (V[y][x] === 0) return true;
      return false;
    }
    // 以降は延伸条件チェック
    for (let y = 0; y < N; y++) {
      for (let x = 0; x < N - 1; x++) {
        if (H[y][x] !== 0) continue;
        const edge = { type: 'H', x, y };
        if (isEdgeExtensionValid(edge, player)) return true;
      }
    }
    for (let y = 0; y < N - 1; y++) {
      for (let x = 0; x < N; x++) {
        if (V[y][x] !== 0) continue;
        const edge = { type: 'V', x, y };
        if (isEdgeExtensionValid(edge, player)) return true;
      }
    }
    return false;
  }

  function endGameIfNoMove() {
    // 現在手番が動けない場合は即終了（パス禁止のため）
    if (!hasAnyMoveFor(turn)) {
      gameOver = true;
      // 最終計算：塗りマス合計は score に反映済み。
      const totalCells = (N - 1) * (N - 1);
      const p1 = score[1], p2 = score[2];
      let result = '';
      if (p1 > p2) result = 'P1 の勝ち';
      else if (p2 > p1) result = 'P2 の勝ち';
      else result = '引き分け';
      updateStatus(`終了｜${result}（全${totalCells}中 P1:${p1} P2:${p2}）`);
      draw();
      return true;
    }
    return false;
  }

  function nextTurn() {
    turn = (turn === 1 ? 2 : 1);
    updateStatus();
    // パス禁止：次手番が動けないならその場で終了
    endGameIfNoMove();
  }

  // イベント設定
  canvas.addEventListener('mousemove', (e) => {
    if (gameOver) return (hoverEdge = null, draw());
    const rect = canvas.getBoundingClientRect();
    const mx = (e.clientX - rect.left) * (canvas.width / rect.width);
    const my = (e.clientY - rect.top) * (canvas.height / rect.height);
    const picked = pickEdge(mx, my);
    if (picked && isEdgeExtensionValid(picked, turn)) {
      hoverEdge = picked;
    } else {
      hoverEdge = null;
    }
    draw();
  });

  canvas.addEventListener('mouseleave', () => {
    hoverEdge = null;
    draw();
  });

  canvas.addEventListener('click', (e) => {
    if (gameOver) return;
    const rect = canvas.getBoundingClientRect();
    const mx = (e.clientX - rect.left) * (canvas.width / rect.width);
    const my = (e.clientY - rect.top) * (canvas.height / rect.height);
    const picked = pickEdge(mx, my);
    if (!picked) return;

    if (!isEdgeExtensionValid(picked, turn)) return;

    // 配置→塗り→ターン移行（手番が打てないなら終了）
    placeEdge(picked, turn);
    draw();

    if (!gameOver) nextTurn();
  });

  restartBtn.addEventListener('click', () => {
    initBoard();
  });

  gridSizeSelect.addEventListener('change', () => {
    N = parseInt(gridSizeSelect.value, 10);
    initBoard();
  });

  // 初期化
  initBoard();
})();
