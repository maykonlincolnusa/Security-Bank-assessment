variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "project_name" {
  type    = string
  default = "trust-score"
}

variable "vpc_cidr" {
  type    = string
  default = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  type    = list(string)
  default = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  type    = list(string)
  default = ["10.0.11.0/24", "10.0.12.0/24"]
}

variable "azs" {
  type    = list(string)
  default = ["us-east-1a", "us-east-1b"]
}

variable "db_name" {
  type    = string
  default = "trustscore"
}

variable "db_username" {
  type    = string
  default = "trustscore"
}

variable "db_password" {
  type      = string
  sensitive = true
}

variable "kms_key_arn" {
  type      = string
  default   = ""
  sensitive = true
}

variable "rds_allocated_storage" {
  type    = number
  default = 100
}

variable "rds_instance_class" {
  type    = string
  default = "db.t3.medium"
}

variable "rds_backup_retention_days" {
  type    = number
  default = 7
}

variable "rds_multi_az" {
  type    = bool
  default = true
}

variable "create_rds_read_replica" {
  type    = bool
  default = false
}

variable "dr_region" {
  type    = string
  default = "us-west-2"
}

variable "eks_kubernetes_version" {
  type    = string
  default = "1.29"
}

variable "eks_endpoint_private_access" {
  type    = bool
  default = true
}

variable "eks_endpoint_public_access" {
  type    = bool
  default = false
}
