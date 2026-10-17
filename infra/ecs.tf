resource "aws_ecs_cluster" "main" {
  name = var.name
}

resource "aws_iam_role" "task_execution" {
  name = "${var.name}-task-execution"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "task_execution" {
  role       = aws_iam_role.task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "secrets" {
  name = "${var.name}-secrets"
  role = aws_iam_role.task_execution.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = aws_secretsmanager_secret.app.arn
    }]
  })
}

resource "aws_iam_role" "core_task" {
  name = "${var.name}-core-task"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "bedrock" {
  name = "${var.name}-bedrock"
  role = aws_iam_role.core_task.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action = ["bedrock:Converse", "bedrock:InvokeModel"]
      Resource = [
        "arn:aws:bedrock:${var.aws_region}::foundation-model/${var.bedrock_model_id}",
        "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:inference-profile/*",
      ]
    }]
  })
}

resource "aws_cloudwatch_log_group" "ingress" {
  name              = "/ecs/${var.name}/ingress"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "core" {
  name              = "/ecs/${var.name}/core"
  retention_in_days = 7
}

locals {
  core_image = var.core_image != "" ? var.core_image : "${aws_ecr_repository.core.repository_url}:latest"
  ingress_image = var.ingress_image != "" ? var.ingress_image : "${aws_ecr_repository.ingress.repository_url}:latest"
  secret_env = [
    { name = "MCP_BEARER_TOKEN", valueFrom = "${aws_secretsmanager_secret.app.arn}:MCP_BEARER_TOKEN::" },
    { name = "POSTGRES_PASSWORD", valueFrom = "${aws_secretsmanager_secret.app.arn}:POSTGRES_PASSWORD::" },
    { name = "POSTGRES_USER", valueFrom = "${aws_secretsmanager_secret.app.arn}:POSTGRES_USER::" },
    { name = "POSTGRES_DB", valueFrom = "${aws_secretsmanager_secret.app.arn}:POSTGRES_DB::" },
  ]
}

resource "aws_ecs_task_definition" "core" {
  family                   = "${var.name}-core"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.task_execution.arn
  task_role_arn            = aws_iam_role.core_task.arn

  container_definitions = jsonencode([{
    name      = "core"
    image     = local.core_image
    essential = true
    portMappings = [{ containerPort = 8001, protocol = "tcp" }]
    environment = [
      { name = "POSTGRES_HOST", value = aws_db_instance.main.address },
      { name = "POSTGRES_PORT", value = "5432" },
      { name = "LLM_PROVIDER", value = "seeded" },
      { name = "BEDROCK_REGION", value = var.aws_region },
      { name = "BEDROCK_MODEL_ID", value = var.bedrock_model_id },
      { name = "CORE_ENGINE_HOST", value = "0.0.0.0" },
      { name = "CORE_ENGINE_PORT", value = "8001" },
    ]
    secrets = local.secret_env
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.core.name
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "core"
      }
    }
  }])
}

resource "aws_ecs_task_definition" "seed" {
  family                   = "${var.name}-seed"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.task_execution.arn

  container_definitions = jsonencode([{
    name        = "seed"
    image       = local.core_image
    essential   = true
    command     = ["executv-seed"]
    environment = [
      { name = "POSTGRES_HOST", value = aws_db_instance.main.address },
      { name = "POSTGRES_PORT", value = "5432" },
    ]
    secrets = local.secret_env
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.core.name
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "seed"
      }
    }
  }])
}

resource "aws_ecs_task_definition" "ingress" {
  family                   = "${var.name}-ingress"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.task_execution.arn

  container_definitions = jsonencode([{
    name      = "ingress"
    image     = local.ingress_image
    essential = true
    command   = ["uvicorn", "ingress_gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
    portMappings = [{ containerPort = 8000, protocol = "tcp" }]
    environment = [
      { name = "CORE_ENGINE_URL", value = "http://core.${var.name}.local:8001" },
      { name = "INGRESS_GATEWAY_HOST", value = "0.0.0.0" },
      { name = "INGRESS_GATEWAY_PORT", value = "8000" },
      { name = "CORS_ORIGINS", value = "http://localhost:5173,https://${aws_cloudfront_distribution.tv.domain_name}" },
    ]
    secrets = [
      { name = "MCP_BEARER_TOKEN", valueFrom = "${aws_secretsmanager_secret.app.arn}:MCP_BEARER_TOKEN::" },
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.ingress.name
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "ingress"
      }
    }
  }])
}

resource "aws_ecs_service" "core" {
  name            = "${var.name}-core"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.core.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.core.id]
    assign_public_ip = false
  }

  service_registries {
    registry_arn = aws_service_discovery_service.core.arn
  }
}

resource "aws_ecs_service" "ingress" {
  name            = "${var.name}-ingress"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.ingress.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.ingress.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.ingress.arn
    container_name   = "ingress"
    container_port   = 8000
  }

  depends_on = [aws_lb_listener.http]
}

resource "aws_service_discovery_private_dns_namespace" "main" {
  name = "${var.name}.local"
  vpc  = aws_vpc.main.id
}

resource "aws_service_discovery_service" "core" {
  name = "core"

  health_check_custom_config {
    failure_threshold = 1
  }

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.main.id
    dns_records {
      type = "A"
      ttl  = 10
    }
  }
}
