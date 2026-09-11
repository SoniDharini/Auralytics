#!/bin/bash
set -euo pipefail
exec > /var/log/auralytics-api-userdata.log 2>&1

# t3.micro = 1 GB RAM. Create swap before any package work.
if [ ! -f /swapfile ]; then
  fallocate -l 1G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
fi
swapon /swapfile || true
grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab

dnf install -y python3 python3-pip unzip
if ! command -v aws >/dev/null 2>&1; then
  dnf install -y aws-cli || dnf install -y awscli
fi

id auralytics >/dev/null 2>&1 || useradd --system --create-home --home-dir /opt/auralytics --shell /sbin/nologin auralytics
mkdir -p /opt/auralytics/api /opt/auralytics/venv
python3 -m venv /opt/auralytics/venv
export PIP_NO_CACHE_DIR=1
/opt/auralytics/venv/bin/pip install --upgrade pip

cat >/usr/local/bin/auralytics-update-api.sh <<'EOF'
#!/bin/bash
set -euo pipefail
export PIP_NO_CACHE_DIR=1
BUCKET="${bucket}"
REGION="${region}"
SSM_PARAM="${ssm_param}"
aws ssm get-parameter --name "$SSM_PARAM" --with-decryption --query Parameter.Value --output text --region "$REGION" > /etc/auralytics.env
chmod 640 /etc/auralytics.env
chown root:auralytics /etc/auralytics.env

until aws s3 cp "s3://$BUCKET/api/current.zip" /tmp/api.zip --region "$REGION"; do
  echo "Waiting for s3://$BUCKET/api/current.zip"
  sleep 15
done

rm -rf /opt/auralytics/api
mkdir -p /opt/auralytics/api
unzip -o /tmp/api.zip -d /opt/auralytics/api
chown -R auralytics:auralytics /opt/auralytics /opt/auralytics/api
/opt/auralytics/venv/bin/pip install --no-cache-dir -r /opt/auralytics/api/requirements.txt
set -a
source /etc/auralytics.env
set +a
cd /opt/auralytics/api
/opt/auralytics/venv/bin/alembic upgrade head || true
systemctl daemon-reload
systemctl enable auralytics-api
systemctl restart auralytics-api
EOF
chmod +x /usr/local/bin/auralytics-update-api.sh

cat >/etc/systemd/system/auralytics-api.service <<'EOF'
[Unit]
Description=Auralytics API microservice
After=network.target

[Service]
Type=simple
User=auralytics
Group=auralytics
WorkingDirectory=/opt/auralytics/api
EnvironmentFile=/etc/auralytics.env
Environment=PYTHONUNBUFFERED=1
Environment=PYTHONDONTWRITEBYTECODE=1
ExecStart=/opt/auralytics/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 --proxy-headers --forwarded-allow-ips=*
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

/usr/local/bin/auralytics-update-api.sh
