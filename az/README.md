# キリシマ AlphaZero

ver2+（捕獲認識ロールアウトMCTS）を**教師**にウォームスタート → **自己対局**で磨く。
盤 N×N の平面を入力に、価値（勝率）＋方策（全辺）を出す小さなConv網を、MCTSで探索しながら鍛える。

## Runpod での回し方
1. GPU ポッド（PyTorch / CUDA テンプレート）を起動。
2. この `az/` フォルダを上げる（git clone か scp）。
3. 依存導入：`pip install -r requirements.txt`
4. **動作確認**（数分・CPUでも可）：`python train.py --smoke`
   - `device=... / teacher samples=... / 勝率=...` が出れば健全。
5. **本番**：`python train.py --hours 3 --N 7`
   - `ckpt/net_latest.pt` を逐次保存、`ckpt/net_final.pt` が最終。
   - ログの「網-MCTS vs 捕獲貪欲 勝率」が上がれば学習が効いている。

## 構成
| ファイル | 役割 | 状態 |
|---|---|---|
| `engine.py`  | ルール | **JS版と5構成で完全一致を検証済み** |
| `mcts.py`    | PUCT探索 | スタブ評価器で向き検証済み（乱択に8/8） |
| `model.py`   | 小Conv網（価値＋方策） | torch（Runpodで初回 smoke） |
| `baseline.py`| 評価用ベースライン（捕獲貪欲） | 済 |
| `train.py`   | 学習本体（ウォームスタート→自己対局） | torch |
| `teacher.ndjson` | 教師対局（ver2+ 自己対局・JSで生成） | 同梱 |

## 主なオプション
`--N 7`（盤）`--hours 3`（時間）`--sims 64`（MCTS探索数）`--games-per-round 24`
`--train-steps 200` `--batch 256` `--warm-epochs 8`

## 後工程
学習済み `net_final.pt` を JS に焼いてブラウザアプリへ。まず 7×7 で本手法を実証し、効けば 9×9 を学習（要・9×9の教師＋学習）。
