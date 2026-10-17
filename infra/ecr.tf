resource "aws_ecr_repository" "core" {
  name         = "${var.name}-core"
  force_delete = true
}

resource "aws_ecr_repository" "ingress" {
  name         = "${var.name}-ingress"
  force_delete = true
}
