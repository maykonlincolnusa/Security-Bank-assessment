output "vpc_id" {
  value = module.vpc.vpc_id
}

output "eks_cluster_name" {
  value = module.eks.cluster_name
}

output "rds_endpoint" {
  value = module.rds.endpoint
}

output "rds_read_replica_endpoint" {
  value = module.rds.read_replica_endpoint
}

output "s3_bucket_name" {
  value = module.s3.bucket_name
}
