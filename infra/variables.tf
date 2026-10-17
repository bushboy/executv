variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "name" {
  type    = string
  default = "executv"
}

variable "ingress_image" {
  type        = string
  default     = ""
  description = "ECR image URI for ingress_gateway. Empty uses the executv-ingress repository :latest tag."
}

variable "core_image" {
  type        = string
  default     = ""
  description = "ECR image URI for core_engine. Empty uses the executv-core repository :latest tag."
}

variable "tv_bucket_name" {
  type    = string
  default = ""
}

variable "bedrock_model_id" {
  type    = string
  default = "anthropic.claude-3-5-haiku-20241022-v1:0"
}

variable "db_username" {
  type    = string
  default = "executv"
}
