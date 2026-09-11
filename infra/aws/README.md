# Deploy Auralytics on AWS EC2 (t3 microservices, no Docker)

Two EC2 **t3.micro** services behind an Application Load Balancer, plus RDS:

```
Browser
   │
   ▼
ALB
   ├─ /api/*  and /health  →  API EC2 (t3.micro, systemd + uvicorn :8000)
   └─ /*                   →  Web EC2 (t3.micro, nginx static SPA)
                              RDS PostgreSQL (db.t3.micro)
```

Same-origin routing keeps cookie auth working. `VITE_API_URL=/api/v1`. No Docker, no Elastic Beanstalk.

Default region: `ap-south-1`.

## 1. Prerequisites

- [AWS CLI v2](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- [Terraform](https://developer.hashicorp.com/terraform/install) >= 1.6
- [Node.js 22](https://nodejs.org/) to build the frontend

```powershell
aws configure
```

If the account has no default VPC:

```powershell
aws ec2 create-default-vpc --region ap-south-1
```

## 2. First deploy

From the repo root:

```powershell
.\infra\aws\deploy.ps1
```

This:

1. Builds the frontend
2. Zips the API and web artifacts
3. Creates RDS, ALB, and two t3.micro instances
4. Uploads zips to S3
5. Each instance installs its runtime (Python or nginx) via user-data and systemd/nginx

Wait 5–10 minutes for first boot (`pip install` on t3.micro is slow). Then open the printed URL and **register a new user**.

Production does not seed the local demo account.

This stack is sized for **t3.micro only**:

- API EC2: `t3.micro` (1 vCPU / 1 GB, 1 GB swap, 1 Uvicorn worker)
- Web EC2: `t3.micro` (nginx)
- RDS: `db.t3.micro`

## 3. API keys

Edit `infra/aws/terraform.tfvars`:

```hcl
groq_api_key    = "your-groq-key"
youtube_api_key = "your-youtube-key"
```

Then `terraform apply` in `infra/aws`, and re-run the API update script (or reboot the API instance) so it reloads `/etc/auralytics.env` from SSM.

## 4. HTTPS

1. ACM certificate in the same region
2. Set `acm_certificate_arn` in `terraform.tfvars`
3. `terraform apply`

## 5. Redeploy code only

```powershell
.\infra\aws\package.ps1
aws s3 cp infra\aws\build\api.zip s3://BUCKET/api/current.zip
aws s3 cp infra\aws\build\web.zip s3://BUCKET/web/current.zip
```

Then SSM `auralytics-update-api.sh` / `auralytics-update-web.sh`, or re-run `.\infra\aws\deploy.ps1`.

## 6. GitHub Actions

Secrets: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`  
Attach `infra/aws/github-actions-policy.json`.

## 7. Tear down

```powershell
cd infra\aws
terraform destroy
```

This deletes RDS data.

## File map

| File | Purpose |
| --- | --- |
| `infra/aws/*.tf` | ALB, two t3 EC2s, RDS, IAM, S3 |
| `infra/aws/templates/user_data_api.sh` | API microservice bootstrap |
| `infra/aws/templates/user_data_web.sh` | Web microservice bootstrap |
| `infra/aws/package.ps1` | Build + zip |
| `infra/aws/deploy.ps1` | First-time deploy |
