# agent info
# agent_name        = "cloudops_agent"
agent_description = "Strands Agent Powered by AWS Bedrock AgentCore"
# agent_env         = "dev"
# agent_version     = "1.0.0"

# General values
tags = {
  "Agent"       = "CloudOps_Agent",
  "Framework"   = "Strands",
  "Environment" = "Dev"
  "Version"     = "v2.0.0"
  "Terraform"   = "True"
}

region = "us-east-1"


# Agentcore runtime configuration
agent_ecr_image_uri   = "public.ecr.aws/nginx/nginx:latest"
network_mode          = "PUBLIC"
server_protocol       = "HTTP"
create_execution_role = true
managed_policy_names  = ["ReadOnlyAccess", "AmazonEC2FullAccess", "AmazonS3FullAccess"]
environment_variables = {
  "LOG_LEVEL"             = "INFO"
  "STRANDS_AGENT_VERSION" = "v2.0.0"
  "BEDROCK_MODEL_ID"      = "anthropic.claude-3-5-sonnet-20240620-v1:0"
  "BEDROCK_MODEL_REGION"  = "us-east-1"
  "BYPASS_TOOL_CONSENT"  = "true"
}

# Agentcore memory configuration
memory_name        = "CloudOps_Agent_Memory"
memory_description = "Long-term memory for CloudOps Agent powered by Bedrock AgentCore"

memory_strategies = {
  semantic = {
    name        = "FactExtractor"
    type        = "SEMANTIC"
    description = "Semantic understanding strategy"
    namespaces  = ["/facts/{actorId}"]
  }
  summary = {
    name        = "SessionSummarizer"
    type        = "SUMMARIZATION"
    description = "Text summarization strategy"
    namespaces  = ["/summaries/{actorId}/{sessionId}"]
  }
  user_pref = {
    name        = "PreferenceLearner"
    type        = "USER_PREFERENCE"
    description = "User preference tracking strategy"
    namespaces  = ["/preferences/{actorId}"]
  }
}

# ECR configuration
ecr_repository_names     = ["cloudops_agent", "cloudops_webapp"]
ecr_image_tag_mutability = "MUTABLE"
ecr_scan_on_push         = false

# VPC configuration
vpc_cidr = "10.0.0.0/16"

public_subnets = {
  "sub1" = {
    cidr_block        = "10.0.1.0/24"
    availability_zone = "us-east-1a"
  }
  "sub2" = {
    cidr_block        = "10.0.2.0/24"
    availability_zone = "us-east-1b"
  }
}

private_subnets = {}

provision_nat_gateway = false

# ALB configuration
alb_internal                   = false
alb_listener_port              = 80
alb_listener_rule_path_pattern = "/*"
health_check_path              = "/"
container_port                 = 80

# ECS configuration
runtime_platform_operating_system_family = "LINUX"
runtime_platform_cpu_architecture        = "ARM64"
container_image                          = ""
launch_type                              = "FARGATE"
desired_count                            = 1

ecs_assign_public_ip = true
ecs_task_cpu         = "1024"
ecs_task_memory      = "2048"

ecs_create_task_role = true

ecs_task_role_managed_policy_arns = [
  "arn:aws:iam::aws:policy/BedrockAgentCoreFullAccess"
]