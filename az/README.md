# キリシマ AlphaZero

ver2+（捕獲認識ロールアウトMCTS）を**教師**にウォームスタート → **並列自己対局**で磨く。
盤 N×N の平面を入力に、価値（勝率）＋方策（全辺）を出す小Conv網を、MCTSで探索しながら鍛える。

## ハードの選び方（重要）
網は極小なので、ボトルネックは GPU でなく **CPUコア数**（自己対局を fork で並列化）。
→ **高vCPUのCPUインスタンス（例：32vCPU）が最適・割安。GPUは不要**（あれば学習に使うが効果小）。
`--workers` をコア数に合わせる。

## Runpod での回し方
1. 高vCPUポッドを起動（CPUでよい）。
2. `git clone https://github.com/kirishima1020/kirishima-game && cd kirishima-game/az`
3. `pip install -r requirements.txt`
4. **動作確認**（数分）：`python train.py --smoke`
5. **1時間様子見**：`python train.py --hours 1 --N 7 --workers 30`
   - 見ながらなら `--shutdown` 不要（終わったら ckpt を回収して手で停止）。
6. 後日の**無人本番**：`python train.py --hours 3 --N 7 --workers 30 --shutdown`
   - ※ `--shutdown` は終了後に `runpodctl stop pod`。**ディスクは揮発なので `--out` を永続ボリュームに**置くこと。

## 主要オプション
`--N 7`（盤）`--hours 1` `--workers 30`（並列数・0で自動=コア-2）`--games-per-worker 2`
`--sims 64`（MCTS探索数）`--train-steps 200` `--batch 256` `--warm-epochs 8` `--shutdown`
`--endgame-cells 9`（空きセル≤これで終盤を厳密ソルバに解かせ、勝敗ラベルを真理化。0で無効）
`--endgame-nodes 60000`（ソルバのノード予算。枝が多すぎる局面は超過で網に退避＝詰まらない）

## 終盤ソルバ（厳密ラベル化）
自己対局が終盤（空きセル≤`--endgame-cells`）に入ったら、弱い網で最後まで打ち切る代わりに
`solve.py` の厳密ソルバ（2人 min-max・置換表つき）が**真の勝敗**を出し、それを中盤局面の
価値ラベルにする。網が一番下手な「総取りの崖」をノイズではなく真理で教えるのが狙い。
ソルバは JS 版（`../lab/solve.js`）と71局面で答えが完全一致・N=3 全幅一致で検証済み。
純Python は約9.6k nodes/秒と遅いので、予算超過は `None` を返し通常の自己対局に退避する。

## ライブで見る（dash.py）
`python dash.py --demo` で見た目をプレビュー。学習を可視化して回すなら train.py の代わりに:
```
tmux new -s k          # ← ssh が切れても学習が死なないよう tmux 内で
python dash.py --hours 1 --N 7 --workers 30   # 引数はそのまま train.py へ
```
スピナー・経過バー・損失スパークライン・eval勝率が 0.12秒ごとに更新。引数なしの素の
`python train.py ...` でも従来どおり動く（ダッシュは被せるだけ）。

## 見るところ
ラウンド毎に `ploss / vloss / games / 網-MCTS vs 捕獲貪欲 勝率`。
- 勝率が上がる＝本物の戦略を獲得中。
- 最初のラウンドの時間で「この時間で何ラウンド回るか」が読める。
- `ckpt/net_latest.pt` 逐次保存・`ckpt/net_final.pt` 最終。

## 構成
| ファイル | 役割 | 検証 |
|---|---|---|
| `engine.py`  | ルール | JS版と5構成で完全一致 ✓ |
| `solve.py`   | 2人厳密終盤ソルバ（厳密ラベル用） | JS版と71局面一致・N=3全幅一致 ✓ |
| `mcts.py`    | PUCT探索 | スタブで向き検証（乱択に8/8）✓ |
| `train.py`   | 並列自己対局＋学習 | 並列プラミング検証済 ✓ / torchはRunpod |
| `model.py`   | 小Conv網（価値＋方策） | torch（Runpodで smoke）|
| `baseline.py`| 評価用（捕獲貪欲） | ✓ |
| `dash.py`    | 学習ライブダッシュボード（train.pyを包む・標準ライブラリのみ） | selftest ✓ |
| `teacher.ndjson` | 教師120局（ver2+ 自己対局） | ✓ |
| `test_mcts.py` / `test_parallel.py` | ローカル検証 | ✓ |

## 後工程
`net_final.pt` を JS に焼いてブラウザアプリへ。まず 7×7 で本手法を実証 → 効けば 9×9 を学習。
