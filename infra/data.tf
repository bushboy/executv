resource "random_password" "db" {
  length  = 24
  special = false
}

resource "random_password" "mcp" {
  length  = 32
  special = false
}

resource "aws_secretsmanager_secret" "app" {
  name = "${var.name}/runtime"
}

resource "aws_secretsmanager_secret_version" "app" {
  secret_id = aws_secretsmanager_secret.app.id
  secret_string = jsonencode({
    MCP_BEARER_TOKEN  = random_password.mcp.result
    POSTGRES_PASSWORD = random_password.db.result
    POSTGRES_USER     = var.db_username
    POSTGRES_DB       = "executv"
  })
}

resource "aws_db_subnet_group" "main" {
  name       = "${var.name}-db"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_db_instance" "main" {
  identifier             = "${var.name}-pg"
  engine                 = "postgres"
  engine_version         = "15"
  instance_class         = "db.t4g.micro"
  allocated_storage      = 20
  db_name                = "executv"
  username               = var.db_username
  password               = random_password.db.result
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.db.id]
  skip_final_snapshot    = true
  publicly_accessible    = false
}
