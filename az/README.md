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

## 見るところ
ラウンド毎に `ploss / vloss / games / 網-MCTS vs 捕獲貪欲 勝率`。
- 勝率が上がる＝本物の戦略を獲得中。
- 最初のラウンドの時間で「この時間で何ラウンド回るか」が読める。
- `ckpt/net_latest.pt` 逐次保存・`ckpt/net_final.pt` 最終。

## 構成
| ファイル | 役割 | 検証 |
|---|---|---|
| `engine.py`  | ルール | JS版と5構成で完全一致 ✓ |
| `mcts.py`    | PUCT探索 | スタブで向き検証（乱択に8/8）✓ |
| `train.py`   | 並列自己対局＋学習 | 並列プラミング検証済 ✓ / torchはRunpod |
| `model.py`   | 小Conv網（価値＋方策） | torch（Runpodで smoke）|
| `baseline.py`| 評価用（捕獲貪欲） | ✓ |
| `teacher.ndjson` | 教師120局（ver2+ 自己対局） | ✓ |
| `test_mcts.py` / `test_parallel.py` | ローカル検証 | ✓ |

## 後工程
`net_final.pt` を JS に焼いてブラウザアプリへ。まず 7×7 で本手法を実証 → 効けば 9×9 を学習。
