resource "aws_db_subnet_group" "this" {
  name       = "${var.project_name}-db-subnets"
  subnet_ids = var.private_subnet_ids
}

resource "aws_security_group" "rds" {
  name        = "${var.project_name}-rds"
  description = "RDS access"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_db_instance" "this" {
  identifier              = "${var.project_name}-postgres"
  engine                  = "postgres"
  engine_version          = "15.4"
  instance_class          = var.instance_class
  allocated_storage       = var.allocated_storage
  db_name                 = var.db_name
  username                = var.db_username
  password                = var.db_password
  storage_encrypted       = true
  kms_key_id              = var.kms_key_arn
  vpc_security_group_ids  = [aws_security_group.rds.id]
  db_subnet_group_name    = aws_db_subnet_group.this.name
  backup_retention_period = var.backup_retention_days
  backup_window           = "03:00-04:00"
  maintenance_window      = "Sun:04:00-Sun:05:00"
  multi_az                = var.multi_az
  copy_tags_to_snapshot   = true
  performance_insights_enabled          = true
  performance_insights_kms_key_id       = var.kms_key_arn
  enabled_cloudwatch_logs_exports       = ["postgresql", "upgrade"]
  auto_minor_version_upgrade            = true
  deletion_protection     = true
  skip_final_snapshot     = false
  final_snapshot_identifier = "${var.project_name}-postgres-final-snapshot"
}

resource "aws_db_instance" "replica" {
  count                    = var.create_read_replica ? 1 : 0
  identifier               = "${var.project_name}-postgres-replica"
  replicate_source_db      = aws_db_instance.this.arn
  instance_class           = var.instance_class
  storage_encrypted        = true
  kms_key_id               = var.kms_key_arn
  copy_tags_to_snapshot    = true
  performance_insights_enabled    = true
  performance_insights_kms_key_id = var.kms_key_arn
  auto_minor_version_upgrade      = true
  deletion_protection             = true
  skip_final_snapshot             = true
}
