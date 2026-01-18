# Agent info
variable "agent_name" {
  description = "Name of the agent"
  type        = string
}

variable "agent_description" {
  description = "Description of the agent"
  type        = string
}

variable "agent_env" {
  description = "Environment of the agent (e.g., dev, staging, prod)"
  type        = string
}

variable "agent_version" {
  description = "Version of the agent"
  type        = string
}

# Default tags
variable "tags" {
  description = "Default tags to apply to all resources"
  type        = map(string)
  default     = {}
}

# AgentCore Runtime configuration
variable "agent_ecr_image_uri" {
  description = "ECR image URI for the agent runtime"
  type        = string
}

variable "network_mode" {
  description = "Network mode for the runtime (PUBLIC or VPC)"
  type        = string
  default     = "PUBLIC"
}

variable "server_protocol" {
  description = "Server protocol for the runtime (HTTP, MCP, A2A)"
  type        = string
  default     = "HTTP"
}

variable "create_execution_role" {
  description = "Whether to create execution role for AgentCore runtime"
  type        = bool
  default     = true
}

variable "managed_policy_names" {
  description = "List of managed policy names to attach to execution role"
  type        = list(string)
  default     = []
}

variable "environment_variables" {
  description = "Environment variables for the runtime"
  type        = map(string)
  default     = {}
}

# AgentCore Memory configuration
variable "memory_name" {
  description = "Name of the AgentCore Memory"
  type        = string
}

variable "memory_description" {
  description = "Description of the AgentCore Memory"
  type        = string
}

variable "memory_strategies" {
  description = "Memory strategies configuration for AgentCore"
  type = map(object({
    name        = string
    type        = string
    description = string
    namespaces  = list(string)
  }))
  default = {}
}

# VPC configuration
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
}

variable "public_subnets" {
  description = "Map of public subnets"
  type = map(object({
    cidr_block        = string
    availability_zone = string
  }))
  default = {}
}

variable "private_subnets" {
  description = "Map of private subnets"
  type = map(object({
    cidr_block        = string
    availability_zone = string
  }))
  default = {}
}

variable "provision_nat_gateway" {
  description = "Whether to provision NAT gateway"
  type        = bool
  default     = false
}

variable "region" {
  description = "AWS region"
  type        = string
}

variable "ecr_repository_names" {
  description = "Name of the ECR repository"
  type        = list(string)
  default     = []
}

variable "ecr_image_tag_mutability" {
  description = "Image tag mutability for ECR repository"
  type        = string
  default     = "MUTABLE"
}

variable "ecr_scan_on_push" {
  description = "Whether to scan images on push to ECR"
  type        = bool
  default     = false
}

# ALB configuration
variable "alb_internal" {
  description = "Whether ALB is internal"
  type        = bool
  default     = false
}

variable "container_port" {
  description = "Port for the container"
  type        = number
}

variable "alb_listener_port" {
  description = "Port for ALB listener"
  type        = number
  default     = 80
}

variable "health_check_path" {
  description = "Health check path for ALB"
  type        = string
  default     = "/"
}

variable "alb_listener_rule_path_pattern" {
  description = "Path pattern for ALB listener rule"
  type        = string
  default     = "/*"
}

# ECS configuration

variable "runtime_platform_operating_system_family" {
  description = "Operating system family for the runtime"
  type        = string
}

variable "runtime_platform_cpu_architecture" {
  description = "CPU architecture for the runtime"
  type        = string
}

variable "runtime_platform_memory_size_gb" {
  description = "Memory size for the runtime"
  type        = number
  default     = 1
}
variable "container_image" {
  description = "Container image URI"
  type        = string
}

variable "ecs_assign_public_ip" {
  description = "Whether to assign public IP to ECS tasks"
  type        = bool
  default     = true
}

variable "launch_type" {
  description = "ECS launch type (FARGATE or EC2)"
  type        = string
  default     = "FARGATE"
}

variable "force_new_deployment" {
  description = "Whether to force new deployment"
  type        = bool
  default     = false
}

variable "wait_for_steady_state" {
  description = "Whether to wait for steady state"
  type        = bool
}

variable "desired_count" {
  description = "Desired number of ECS tasks"
  type        = number
  default     = 1
}

variable "ecs_task_cpu" {
  description = "CPU units for ECS task"
  type        = string
  default     = "1024"
}

variable "ecs_task_memory" {
  description = "Memory for ECS task"
  type        = string
  default     = "2048"
}

variable "ecs_create_task_role" {
  description = "Whether to create task role for ECS"
  type        = bool
  default     = true
}

variable "ecs_task_role_managed_policy_arns" {
  description = "List of managed policy ARNs for ECS task role"
  type        = list(string)
  default     = []
}
