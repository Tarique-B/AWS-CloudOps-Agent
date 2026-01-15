locals {
  name_prefix = "${var.agent_name}_${var.agent_env}"
}

# NOTE: Using my own modules for Agentcore,VPC,ECR,ECS,ALB. Refering from respective repos.

module "ecr" {
  source               = "git::https://github.com/Tarique-B-DevOps/Terraform-AWS-ECR-ECS.git//modules/ecr?ref=main"
  count                = length(var.ecr_repository_names)
  repository_name      = var.ecr_repository_names[count.index]
  image_tag_mutability = var.ecr_image_tag_mutability
  scan_on_push         = var.ecr_scan_on_push
}

module "agentcore_memory" {
  source = "git::https://github.com/Tarique-B-DevOps/Terraform-AWS-AgentCore.git//modules/agentcore-memory?ref=main"

  memory_name        = local.name_prefix
  memory_description = var.memory_description
  memory_strategies  = var.memory_strategies
}

module "agentcore_runtime" {
  source = "git::https://github.com/Tarique-B-DevOps/Terraform-AWS-AgentCore.git//modules/agentcore-runtime?ref=main"

  agent_runtime_name    = local.name_prefix
  description           = var.agent_description
  agent_ecr_image_uri   = module.ecr[0].repository_url
  network_mode          = var.network_mode
  server_protocol       = var.server_protocol
  create_execution_role = var.create_execution_role
  managed_policy_names  = var.managed_policy_names
  environment_variables = module.agentcore_memory.memory_id != "" ? merge(var.environment_variables, {
    "AGENTCORE_LTM_MEMORY_ID" = module.agentcore_memory.memory_id
  }) : var.environment_variables
}


module "vpc" {
  source                = "git::https://github.com/Tarique-B-DevOps/Terraform-AWS-VPC-EKS.git//modules/vpc?ref=main"
  vpc_cidr              = var.vpc_cidr
  public_subnets        = var.public_subnets
  private_subnets       = var.private_subnets
  provision_nat_gateway = var.provision_nat_gateway
  environment           = local.name_prefix
}

module "alb" {
  source = "git::https://github.com/Tarique-B-DevOps/Terraform-AWS-ECR-ECS.git//modules/alb?ref=main"

  name_prefix                = local.name_prefix
  vpc_id                     = module.vpc.vpc_id
  subnet_ids                 = module.vpc.public_subnet_ids
  internal                   = var.alb_internal
  target_port                = var.container_port
  listener_port              = var.alb_listener_port
  health_check_path          = var.health_check_path
  listener_rule_path_pattern = var.alb_listener_rule_path_pattern
}

module "ecs" {
  source = "git::https://github.com/Tarique-B-DevOps/Terraform-AWS-ECR-ECS.git//modules/ecs?ref=main"

  name_prefix      = "${local.name_prefix}_Webapp"
  cluster_name     = "${local.name_prefix}_Webapp"
  region           = var.region
  vpc_id           = module.vpc.vpc_id
  subnet_ids       = module.vpc.public_subnet_ids
  assign_public_ip = var.ecs_assign_public_ip

  container_name  = "${local.name_prefix}_Webapp"
  container_image = module.ecr[1].repository_url
  container_port  = var.container_port

  launch_type   = var.launch_type
  desired_count = var.desired_count
  task_cpu      = var.ecs_task_cpu
  task_memory   = var.ecs_task_memory

  target_group_arn      = module.alb.target_group_arn
  alb_security_group_id = module.alb.security_group_id

  create_task_role              = var.ecs_create_task_role
  task_role_managed_policy_arns = var.ecs_task_role_managed_policy_arns


  depends_on = [module.vpc, module.ecr, module.alb]
}
