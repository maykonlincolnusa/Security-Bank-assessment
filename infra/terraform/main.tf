terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.40"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

provider "aws" {
  alias  = "dr"
  region = var.dr_region
}

module "vpc" {
  source             = "./modules/vpc"
  name               = var.project_name
  vpc_cidr            = var.vpc_cidr
  public_subnet_cidrs  = var.public_subnet_cidrs
  private_subnet_cidrs = var.private_subnet_cidrs
  azs                = var.azs
}

module "iam" {
  source       = "./modules/iam"
  project_name = var.project_name
}

module "eks" {
  source              = "./modules/eks"
  project_name        = var.project_name
  vpc_id              = module.vpc.vpc_id
  private_subnet_ids  = module.vpc.private_subnet_ids
  public_subnet_ids   = module.vpc.public_subnet_ids
  cluster_role_arn    = module.iam.eks_cluster_role_arn
  node_role_arn       = module.iam.eks_node_role_arn
  kubernetes_version  = var.eks_kubernetes_version
  endpoint_private_access = var.eks_endpoint_private_access
  endpoint_public_access  = var.eks_endpoint_public_access
  kms_key_arn         = var.kms_key_arn
}

module "rds" {
  source             = "./modules/rds"
  project_name       = var.project_name
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  db_name            = var.db_name
  db_username        = var.db_username
  db_password        = var.db_password
  kms_key_arn        = var.kms_key_arn
  allocated_storage  = var.rds_allocated_storage
  instance_class     = var.rds_instance_class
  backup_retention_days = var.rds_backup_retention_days
  multi_az           = var.rds_multi_az
  create_read_replica = var.create_rds_read_replica
}

module "s3" {
  source       = "./modules/s3"
  project_name = var.project_name
  kms_key_arn  = var.kms_key_arn
}
