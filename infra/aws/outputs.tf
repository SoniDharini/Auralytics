output "app_url" {
  description = "Public load balancer URL"
  value       = local.https_enabled ? "https://${aws_lb.app.dns_name}" : "http://${aws_lb.app.dns_name}"
}

output "alb_dns_name" {
  value = aws_lb.app.dns_name
}

output "api_instance_id" {
  value = aws_instance.api.id
}

output "web_instance_id" {
  value = aws_instance.web.id
}

output "deploy_bucket" {
  value = aws_s3_bucket.deploy.bucket
}

output "rds_endpoint" {
  value     = aws_db_instance.postgres.address
  sensitive = true
}

output "aws_region" {
  value = var.aws_region
}

output "aws_account_id" {
  value = data.aws_caller_identity.current.account_id
}
