#!/usr/bin/env bash
# キリシマ学習ランチャ（tmux）。素の Ctrl-P/Ctrl-L は潰さず、プレフィックス方式で操作する。
#   Ctrl-B → P … 学習パネル ⇄ シェル を切替（両方生きたまま・学習は止まらない）
#   Ctrl-B → L … 学習パネルへ一発で戻る
#   Ctrl-B → D … 丸ごと裏へ（detach・学習は継続）
#   学習パネルで Ctrl-C … 学習を停止
#   ssh が切れても学習は継続。もう一度 `./k.sh` で再入場（attach）。
# 使い方: cd ~/kirishima-game/az && ./k.sh [--hours 3 --N 7 --workers 30]
set -uo pipefail
export LANG=C.UTF-8 LC_ALL=C.UTF-8 PYTHONUTF8=1   # 日本語描画のため UTF-8 を強制
S=k
command -v tmux >/dev/null || { apt-get update -qq && apt-get install -y -qq tmux; }

# 既に動いていれば、新規起動せず再入場するだけ。
if tmux has-session -t "$S" 2>/dev/null; then exec tmux attach -t "$S"; fi

ARGS="${*:---hours 3 --N 7 --workers 30 --eval-every 1}"
tmux new-session  -d -s "$S" -n learn -c "$PWD"
tmux send-keys    -t "$S:learn" "LANG=C.UTF-8 LC_ALL=C.UTF-8 PYTHONUTF8=1 python dash.py $ARGS" C-m
tmux new-window   -t "$S" -n shell -c "$PWD"
# プレフィックス（Ctrl-B）後の1文字に割当。素の Ctrl-P/Ctrl-L は無傷。
tmux bind-key p last-window
tmux bind-key l select-window -t "$S:learn"
tmux select-window -t "$S:learn"
exec tmux attach -t "$S"
