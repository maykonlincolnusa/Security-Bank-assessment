output "endpoint" {
  value = aws_db_instance.this.endpoint
}

output "read_replica_endpoint" {
  value = try(aws_db_instance.replica[0].endpoint, null)
}
