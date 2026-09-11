variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "ap-south-1"
}

variable "project_name" {
  description = "Short name used for AWS resource prefixes"
  type        = string
  default     = "auralytics"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "acm_certificate_arn" {
  description = "Optional ACM certificate ARN in this region. Enables HTTPS on the ALB."
  type        = string
  default     = ""
}

variable "groq_api_key" {
  description = "Groq API key"
  type        = string
  default     = ""
  sensitive   = true
}

variable "youtube_api_key" {
  description = "YouTube Data API v3 key"
  type        = string
  default     = ""
  sensitive   = true
}
