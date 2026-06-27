#!/usr/bin/env bash
# キリシマ 対局ログ受信エンドポイントの一括セットアップ（Ubuntu / root 想定）
# Node導入 → ingest.js常駐化(systemd) → Caddyで自動HTTPS(sslip.io, ドメイン不要) → ENDPOINT表示
set -uo pipefail
ING_URL="https://kirishima1020.github.io/kirishima-game/ingest.js"
export DEBIAN_FRONTEND=noninteractive
say(){ echo; echo "== $* =="; }

IP=$(curl -fsS https://api.ipify.org 2>/dev/null || curl -fsS https://ifconfig.me 2>/dev/null)
DOMAIN="$(echo "$IP" | tr '.' '-').sslip.io"
say "公開IP=$IP / ドメイン=$DOMAIN"

say "Node 22 導入"
if ! command -v node >/dev/null 2>&1; then
  curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && apt-get install -y nodejs
fi
node -v || { echo "Node導入に失敗。出力を桐島へ。"; exit 1; }

say "ingest.js 配置"
mkdir -p /opt/kirishima
for i in 1 2 3 4 5 6; do curl -fsSL "$ING_URL" -o /opt/kirishima/ingest.js && break; echo "取得待ち($i)…"; sleep 10; done
head -1 /opt/kirishima/ingest.js || { echo "ingest.js 取得に失敗。"; exit 1; }

say "ingest サービス化（systemd / :8788 / 自動再起動）"
cat > /etc/systemd/system/kirishima-ingest.service <<'EOF'
[Unit]
Description=Kirishima game-log ingest
After=network.target
[Service]
ExecStart=/usr/bin/node /opt/kirishima/ingest.js 8788 /opt/kirishima/games.ndjson
Restart=always
User=root
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload && systemctl enable --now kirishima-ingest
sleep 1; systemctl is-active kirishima-ingest || journalctl -u kirishima-ingest -n 20 --no-pager

say "Caddy 導入（自動HTTPS）"
if ! command -v caddy >/dev/null 2>&1; then
  apt-get install -y debian-keyring debian-archive-keyring apt-transport-https curl gnupg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' > /etc/apt/sources.list.d/caddy-stable.list
  apt-get update && apt-get install -y caddy
fi
cat > /etc/caddy/Caddyfile <<EOF
$DOMAIN {
    reverse_proxy localhost:8788
}
EOF
systemctl restart caddy; sleep 3

say "確認"
echo -n "ローカル ingest: "; curl -fsS http://localhost:8788/ 2>/dev/null || echo "(応答なし)"
echo
echo -n "HTTPS（初回は証明書取得に十数秒かかることあり）: "; curl -fsS "https://$DOMAIN/" 2>/dev/null || echo "(まだ→数十秒後: curl https://$DOMAIN/ )"
echo
echo "##################################################"
echo "#  ENDPOINT = https://$DOMAIN/ingest"
echo "##################################################"
