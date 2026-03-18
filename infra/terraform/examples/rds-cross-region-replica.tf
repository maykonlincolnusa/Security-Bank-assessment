# Example only: cross-region RDS replica
# Usage: apply in a dedicated DR workspace/account after primary DB exists.

provider "aws" {
  alias  = "primary"
  region = "us-east-1"
}

provider "aws" {
  alias  = "dr"
  region = "us-west-2"
}

variable "primary_db_arn" {
  type        = string
  description = "ARN of primary RDS instance"
}

variable "kms_key_arn_dr" {
  type        = string
  description = "KMS key ARN in DR region"
}

resource "aws_db_instance" "cross_region_replica" {
  provider                    = aws.dr
  identifier                  = "trust-score-postgres-dr-replica"
  replicate_source_db         = var.primary_db_arn
  instance_class              = "db.t3.medium"
  storage_encrypted           = true
  kms_key_id                  = var.kms_key_arn_dr
  copy_tags_to_snapshot       = true
  auto_minor_version_upgrade  = true
  deletion_protection         = true
  skip_final_snapshot         = true
  publicly_accessible         = false
}
