# ECR outputs
output "ecr_repository_urls" {
  description = "URLs of the ECR repositories"
  value       = [for repo in module.ecr : repo.repository_url]
}

output "ecr_repository_names" {
  description = "Names of the ECR repositories"
  value       = [for repo in module.ecr : repo.repository_name]
}

output "ecr_repository_url" {
  description = "URL of the first ECR repository (for backward compatibility)"
  value       = length(module.ecr) > 0 ? module.ecr[0].repository_url : null
}

output "ecr_repository_name" {
  description = "Name of the first ECR repository (for backward compatibility)"
  value       = length(module.ecr) > 0 ? module.ecr[0].repository_name : null
}

# AgentCore Memory outputs
output "agentcore_memory_id" {
  description = "ID of the AgentCore Memory"
  value       = try(module.agentcore_memory.memory_id, null)
}

output "agentcore_memory_arn" {
  description = "ARN of the AgentCore Memory"
  value       = try(module.agentcore_memory.memory_arn, null)
}

# AgentCore Runtime outputs
output "agentcore_runtime_id" {
  description = "ID of the AgentCore Runtime"
  value       = try(module.agentcore_runtime.runtime_id, null)
}

output "agentcore_runtime_arn" {
  description = "ARN of the AgentCore Runtime"
  value       = try(module.agentcore_runtime.runtime_arn, null)
}

output "agentcore_runtime_endpoint" {
  description = "Endpoint of the AgentCore Runtime"
  value       = try(module.agentcore_runtime.runtime_endpoint, null)
}

# VPC outputs
output "vpc_id" {
  description = "ID of the VPC"
  value       = module.vpc.vpc_id
}

output "vpc_cidr" {
  description = "CIDR block of the VPC"
  value       = var.vpc_cidr
}

output "public_subnet_ids" {
  description = "IDs of public subnets"
  value       = module.vpc.public_subnet_ids
}

output "private_subnet_ids" {
  description = "IDs of private subnets"
  value       = module.vpc.private_subnet_ids
}

# ALB outputs
output "alb_dns_name" {
  description = "DNS name of the ALB"
  value       = module.alb.alb_dns_name
}

output "alb_arn" {
  description = "ARN of the ALB"
  value       = module.alb.alb_arn
}

output "target_group_arn" {
  description = "ARN of the target group"
  value       = module.alb.target_group_arn
}

# ECS outputs
output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = module.ecs.cluster_name
}

output "ecs_cluster_arn" {
  description = "ARN of the ECS cluster"
  value       = module.ecs.cluster_arn
}

output "ecs_service_name" {
  description = "Name of the ECS service"
  value       = module.ecs.service_name
}

output "ecs_service_arn" {
  description = "ARN of the ECS service"
  value       = module.ecs.service_arn
}
