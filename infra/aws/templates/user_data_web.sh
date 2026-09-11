#!/bin/bash
set -euo pipefail
exec > /var/log/auralytics-web-userdata.log 2>&1

dnf install -y nginx unzip
if ! command -v aws >/dev/null 2>&1; then
  dnf install -y aws-cli || dnf install -y awscli
fi

mkdir -p /var/www/auralytics

cat >/etc/nginx/conf.d/auralytics.conf <<'EOF'
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;
    root /var/www/auralytics;
    index index.html;
    client_max_body_size 25m;
    gzip on;
    gzip_types text/plain text/css application/javascript application/json image/svg+xml;

    location / {
        try_files $uri $uri/ /index.html;
    }
}
EOF
rm -f /etc/nginx/conf.d/default.conf || true

cat >/usr/local/bin/auralytics-update-web.sh <<'EOF'
#!/bin/bash
set -euo pipefail
BUCKET="${bucket}"
REGION="${region}"

until aws s3 cp "s3://$BUCKET/web/current.zip" /tmp/web.zip --region "$REGION"; do
  echo "Waiting for s3://$BUCKET/web/current.zip"
  sleep 15
done

rm -rf /var/www/auralytics
mkdir -p /var/www/auralytics
unzip -o /tmp/web.zip -d /var/www/auralytics
chown -R nginx:nginx /var/www/auralytics
systemctl enable nginx
systemctl restart nginx
EOF
chmod +x /usr/local/bin/auralytics-update-web.sh

/usr/local/bin/auralytics-update-web.sh
