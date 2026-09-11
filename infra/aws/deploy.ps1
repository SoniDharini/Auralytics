#Requires -Version 5.1
<#
.SYNOPSIS
  Deploy Auralytics to EC2 t3 microservices (API + web) behind an ALB. No Docker.

.EXAMPLE
  .\infra\aws\deploy.ps1
#>
$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $RepoRoot

function Require-Command($command) {
  if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
    throw "Missing required command: $command"
  }
}

Require-Command aws
Require-Command terraform
Require-Command npm

Write-Host "Checking AWS identity..."
$Account = aws sts get-caller-identity --query Account --output text
if (-not $Account) { throw "AWS CLI is not authenticated. Run: aws configure" }

$InfraDir = Join-Path $RepoRoot "infra\aws"
Set-Location $InfraDir

if (-not (Test-Path "terraform.tfvars")) {
  Copy-Item "terraform.tfvars.example" "terraform.tfvars"
  Write-Host "Created infra/aws/terraform.tfvars from the example. Add API keys if needed, then re-run."
}

Write-Host "Packaging API and web artifacts..."
& (Join-Path $InfraDir "package.ps1")

$ApiZip = Join-Path $InfraDir "build\api.zip"
$WebZip = Join-Path $InfraDir "build\web.zip"
if (-not (Test-Path $ApiZip) -or -not (Test-Path $WebZip)) {
  throw "Package zips were not created."
}

Write-Host "Terraform init/apply (RDS + ALB + t3.micro API/web)..."
terraform init
terraform apply -auto-approve

$Bucket = terraform output -raw deploy_bucket
$AppUrl = terraform output -raw app_url
$Region = terraform output -raw aws_region
$ApiId = terraform output -raw api_instance_id
$WebId = terraform output -raw web_instance_id

Write-Host "Uploading artifacts to S3..."
aws s3 cp $ApiZip "s3://$Bucket/api/current.zip" --region $Region
aws s3 cp $WebZip "s3://$Bucket/web/current.zip" --region $Region

Write-Host "Triggering instance updates via SSM if agents are online..."
try {
  aws ssm send-command --instance-ids $ApiId --document-name "AWS-RunShellScript" --parameters "commands=/usr/local/bin/auralytics-update-api.sh" --region $Region | Out-Null
  aws ssm send-command --instance-ids $WebId --document-name "AWS-RunShellScript" --parameters "commands=/usr/local/bin/auralytics-update-web.sh" --region $Region | Out-Null
} catch {
  Write-Host "SSM not ready yet. First-boot user-data will pull artifacts from S3."
}

Write-Host ""
Write-Host "Deploy started."
Write-Host "App URL: $AppUrl"
Write-Host "API instance: $ApiId   Web instance: $WebId"
Write-Host "First boot can take 5-10 minutes (package install + pip). Then register a new account."
Write-Host "Demo users are not seeded in production."
Write-Host "If SSM is not ready yet, the instances will still pick up s3://$Bucket once user-data finishes waiting."
