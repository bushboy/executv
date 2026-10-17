output "alb_dns_name" {
  value = aws_lb.main.dns_name
}

output "mcp_url" {
  value = "http://${aws_lb.main.dns_name}/mcp"
}

output "tv_url" {
  value = "https://${aws_cloudfront_distribution.tv.domain_name}"
}

output "mcp_bearer_secret_arn" {
  value = aws_secretsmanager_secret.app.arn
}

output "seed_task_definition" {
  value = aws_ecs_task_definition.seed.arn
}

output "core_image" {
  value = aws_ecr_repository.core.repository_url
}

output "ingress_image" {
  value = aws_ecr_repository.ingress.repository_url
}

output "tv_distribution_id" {
  value = aws_cloudfront_distribution.tv.id
}
