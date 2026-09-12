# AWS CloudOps Agent

[![AWS](https://img.shields.io/badge/AWS-Bedrock-orange)](https://aws.amazon.com/bedrock/)
[![AgentCore](https://img.shields.io/badge/AWS-AgentCore-blue)](https://aws.amazon.com/bedrock/agentcore/)
[![Strands](https://img.shields.io/badge/Strands-Agent%20Framework-green)](https://strandsagents.com/latest/)
[![Terraform](https://img.shields.io/badge/IaC-Terraform-purple)](https://www.terraform.io/)
[![Jenkins](https://img.shields.io/badge/CI%2FCD-Jenkins-red)](https://www.jenkins.io/)
[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Conversational AI Agent for Day-to-Day AWS Operations** | Manage EC2, IAM, S3, and more through natural language with persistent memory, fully automated deployment on AWS Bedrock AgentCore.

---

## 🎯 Overview

The **AWS CloudOps Assistant** is an intelligent AI agent designed to simplify day-to-day AWS operations through natural language conversations. Instead of navigating the AWS Console, simply tell the agent what you need—managing EC2 instances, IAM operations, querying resources, code and AWS CLI commands generation, cost analysis, security and network management, and it handles the rest.

Built on the **Strands Agent Framework** and powered by **AWS Bedrock LLMs**, this project showcases:

- **Agentic AI Capabilities**: Autonomous task execution with tool use, reasoning, and memory
- **DevOps Best Practices**: Infrastructure as Code, CI/CD automation, containerized deployments
- **Enterprise-Ready Architecture**: Managed serverless hosting on AWS Bedrock AgentCore

<video width="640" height="360" controls>
  <source src="https://github.com/user-attachments/assets/5b8b2922-f951-4169-9c16-6383734507d3" type="video/mp4">
  Your browser does not support the video tag.
</video>

[🎥 Click here to watch the demo video in a new tab](https://github.com/user-attachments/assets/5b8b2922-f951-4169-9c16-6383734507d3)

---

## 🤖 Agentic Capabilities

### What Makes This Agent Intelligent

| Capability | Description |
|------------|-------------|
| **Tool Use** | Executes real AWS operations via `use_aws` tool—create, modify, query, and delete resources |
| **Contextual Memory** | Remembers resources created, user preferences, and conversation history across sessions |
| **Reasoning** | Understands intent, asks clarifying questions when needed, and explains actions before executing |
| **Guardrails** | Focused exclusively on AWS operations; declines off-topic requests gracefully |
| **Streaming Responses** | Real-time response streaming for immediate feedback during long operations |


---

## 🛠️ Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **AI Agent Framework** | [Strands Agent](https://strandsagents.com/latest/) | Orchestrates tool use, reasoning, and conversation flow |
| **LLM Platform** | AWS Bedrock | Foundation model for natural language understanding and generation |
| **Agent Hosting** | AWS Bedrock AgentCore Runtime | Managed serverless infrastructure for running agents at scale |
| **Long-Term Memory** | AWS Bedrock AgentCore Memory | Persistent storage for user context, resource tracking, and session history |
| **Web Interface** | Streamlit | Interactive chat UI with session management and real-time streaming |
| **API Layer** | FastAPI | High-performance REST API with async support |
| **Containerization** | Docker & Docker Buildx | container builds |
| **Infrastructure as Code** | Terraform | Modular, reusable infrastructure definitions |
| **CI/CD Pipeline** | Jenkins | Automated build, scan, test, and deployment workflows |
| **Backend Language** | Python 3.11+ | Agent logic, API endpoints, and integrations |

---

## ✨ Features

### 🧠 Intelligent Agent

- **Natural Language Interface**: Describe what you want in plain English
- **Autonomous Execution**: Agent plans and executes multi-step operations
- **Memory Persistence**: Resources and context remembered across sessions using AgentCore Memory
- **Safe Operations**: Confirmation prompts for destructive actions, clear explanations before execution
- **Markdown Responses**: Structured output with tables for resource listings

### 💬 Streamlit Web Interface

- **Real-Time Streaming**: See agent responses as they're generated
- **Session Management**: Unique session IDs with persistent actor identity
- **Agent Status Display**: Live connection status to AgentCore runtime
- **Memory Indicators**: Visual confirmation when memory is active
- **Chat History**: Full conversation history within sessions

### ⚙️ Infrastructure & Deployment

- **Modular Terraform**: Reusable modules for ECR, AgentCore, VPC, ALB, ECS
- **Multi-Environment Support**: Deploy to dev, staging, or prod with parameter switches
- **Security Scanning**: Trivy for IaC and container images, Snyk for code analysis
- **Approval Gates**: Manual approval steps for infrastructure changes
- **Slack Notifications**: Pipeline status updates at every stage

---

## 📖 Use Cases

The AWS CloudOps Assistant excels at everyday AWS operations. Below are demonstrated use cases with video walkthroughs.

### 🖥️ Resource Management

#### Create an EC2 Instance
> "Create an EC2 instance in us-east-1 using the latest Amazon Linux 2023 AMI with t2.micro instance type. Use default VPC and subnet, no key pair needed, and use default security group settings."

The agent creates the instance and **automatically stores the instance ID, ARN, and configuration in memory** for future reference.

<video width="640" height="360" controls>
  <source src="https://github.com/user-attachments/assets/c3408c76-f31f-4a0c-a5ca-ca00f8e56f2f" type="video/mp4">
  Your browser does not support the video tag.
</video>

[🎥 Click here to watch EC2 Instance Creation in a new tab](https://github.com/user-attachments/assets/c3408c76-f31f-4a0c-a5ca-ca00f8e56f2f)

---

#### Stop a Previously Created Instance
> "Stop the EC2 instance that you created previously."

The agent **retrieves the instance ID from memory** and stops it—no need to specify IDs manually.

<video width="640" height="360" controls>
  <source src="https://github.com/user-attachments/assets/312215db-7dc3-4722-9193-6ad510e95da2" type="video/mp4">
  Your browser does not support the video tag.
</video>

[🎥 Click here to watch EC2 Instance Stop (Memory Demo) in a new tab](https://github.com/user-attachments/assets/312215db-7dc3-4722-9193-6ad510e95da2)

---

### 🔐 IAM Policy Management

#### Attach a Policy to a User
> "Attach the policy AmazonEC2FullAccess to the IAM user named JohnDoe."

The agent attaches the managed policy and **stores the action in memory**.

<video width="640" height="360" controls>
  <source src="https://github.com/user-attachments/assets/c1c01592-7fa1-4c3e-9532-94e31a8e9c8f" type="video/mp4">
  Your browser does not support the video tag.
</video>

[🎥 Click here to watch IAM Policy Attachment in a new tab](https://github.com/user-attachments/assets/c1c01592-7fa1-4c3e-9532-94e31a8e9c8f)

---

#### Detach a Policy from a User
> "Detach the policy from the IAM user JohnDoe that you attached previously."

**Even in a new session**, the agent recalls the previous action from memory and detaches the correct policy.

<video width="640" height="360" controls>
  <source src="https://github.com/user-attachments/assets/cce726c6-bb43-439e-8099-c511baaa7502" type="video/mp4">
  Your browser does not support the video tag.
</video>

[🎥 Click here to watch IAM Policy Detachment (Cross-Session Memory) in a new tab](https://github.com/user-attachments/assets/cce726c6-bb43-439e-8099-c511baaa7502)

---

### 💻 Code Generation

#### Generate a Boto3 Script
> "Generate a Python script using Boto3 that iterates through all S3 buckets and stores their information in a CSV file."

The agent generates **ready-to-use Python code** with proper error handling, CSV formatting, and AWS best practices.

<video width="640" height="360" controls>
  <source src="https://github.com/user-attachments/assets/802278ba-0967-4b89-937a-dc1fb4601e43" type="video/mp4">
  Your browser does not support the video tag.
</video>

[🎥 Click here to watch Boto3 Script Generation in a new tab](https://github.com/user-attachments/assets/802278ba-0967-4b89-937a-dc1fb4601e43)

---

### 📋 Command Suggestions

#### Get AWS CLI Commands
> "Give me the AWS CLI command to copy a local folder to an S3 bucket."

The agent provides the **exact CLI command** with explanations of flags and options for your specific use case.

<video width="640" height="360" controls>
  <source src="https://github.com/user-attachments/assets/5efb297e-8b63-4b1b-bc17-3a846729ffc7" type="video/mp4">
  Your browser does not support the video tag.
</video>

[🎥 Click here to watch AWS CLI Command Suggestion in a new tab](https://github.com/user-attachments/assets/5efb297e-8b63-4b1b-bc17-3a846729ffc7)

---

### 🔍 Additional Use Cases

The AWS CloudOps Assistant can handle a wide range of additional AWS operations:

#### Cost Analysis
> "Analyze my AWS costs for the last 30 days and identify the top 5 services by spending. Show me cost optimization recommendations."

The agent retrieves cost data from AWS Cost Explorer, generates detailed reports, and provides actionable recommendations for reducing expenses.

#### Alarm Creation
> "Create a CloudWatch alarm that triggers when CPU utilization exceeds 80% for any EC2 instance in us-east-1. Send notifications to my SNS topic."

The agent creates the alarm with proper thresholds, associates it with the SNS topic, and configures evaluation periods.

#### CloudTrail Log Analysis
> "Analyze CloudTrail logs from the past 7 days and show me all failed IAM authentication attempts. Identify any suspicious access patterns."

The agent queries CloudTrail logs, filters for security events, and provides insights on access patterns and potential security issues.

#### Resource Tagging
> "Tag all EC2 instances in us-east-1 with Environment=Production and Project=WebApp. Also add a CostCenter tag with value IT-001."

The agent identifies all instances, applies the specified tags consistently, and verifies the tagging operation.

#### Security Group Rule Management
> "Add an inbound rule to security group sg-12345678 allowing SSH access (port 22) from IP 203.0.113.0/24. Also remove any existing rules that allow access from 0.0.0.0/0 on port 22."

The agent modifies security group rules, adds new rules with proper CIDR blocks, and removes overly permissive rules for enhanced security.

#### S3 Bucket Operations
> "Create an S3 bucket lifecycle policy that moves objects older than 30 days to Glacier storage and deletes objects older than 365 days."

The agent creates the lifecycle configuration, applies it to the bucket, and ensures proper transition and expiration rules.

#### Lambda Function Management
> "Update the environment variables for my Lambda function 'processData' to set LOG_LEVEL=DEBUG and TIMEOUT=300."

The agent updates the Lambda function configuration, modifies environment variables, and verifies the changes.

#### RDS Database Operations
> "Create a snapshot of my RDS database instance 'prod-db' and name it 'prod-db-backup-2024-01-15'. Also show me the last 5 snapshots."

The agent creates the database snapshot, monitors the snapshot creation process, and lists recent snapshots for backup management.

#### VPC Configuration
> "Create a new VPC with CIDR 10.0.0.0/16 in us-east-1. Set up public and private subnets across two availability zones, and configure an internet gateway and NAT gateway."

The agent creates the complete VPC infrastructure with proper networking components, route tables, and gateway configurations.

#### Auto Scaling Management
> "Configure an auto scaling group for my application that scales between 2 and 10 instances based on CPU utilization. Set up a target tracking policy to maintain 50% CPU."

The agent creates the auto scaling group, configures scaling policies, and sets up CloudWatch alarms for automatic scaling.

#### Backup and Disaster Recovery
> "Create a backup plan for all EBS volumes in us-east-1. Schedule daily backups with 7-day retention and weekly backups with 30-day retention."

The agent sets up AWS Backup plans, configures backup schedules, and applies retention policies for disaster recovery compliance.

#### Compliance Reporting
> "Generate a compliance report showing all S3 buckets that are publicly accessible. Also check which buckets don't have encryption enabled."

The agent audits S3 bucket configurations, identifies security and compliance issues, and generates a detailed report with remediation recommendations.

---

## 🚀 Automated Agent Lifecycle on AgentCore

The entire agent lifecycle—from build to deployment to destruction—is fully automated through Terraform and Jenkins.

### 📦 Terraform Modular Architecture

Infrastructure is organized using custom Terraform modules that I developed and maintain in separate repositories:

| Module | Source Repository | Resources Created |
|--------|-------------------|-------------------|
| **ECR** | [Terraform-AWS-ECR-ECS](https://github.com/Tarique-B-DevOps/Terraform-AWS-ECR-ECS) | Container registries for agent and app images |
| **AgentCore Memory** | [Terraform-AWS-AgentCore](https://github.com/Tarique-B-DevOps/Terraform-AWS-AgentCore) | Long-term memory store for agent context |
| **AgentCore Runtime** | [Terraform-AWS-AgentCore](https://github.com/Tarique-B-DevOps/Terraform-AWS-AgentCore) | Managed serverless agent hosting |
| **VPC** | [Terraform-AWS-VPC-EKS](https://github.com/Tarique-B-DevOps/Terraform-AWS-VPC-EKS) | Network infrastructure with public/private subnets |
| **ALB** | [Terraform-AWS-ECR-ECS](https://github.com/Tarique-B-DevOps/Terraform-AWS-ECR-ECS) | Application Load Balancer for web traffic |
| **ECS** | [Terraform-AWS-ECR-ECS](https://github.com/Tarique-B-DevOps/Terraform-AWS-ECR-ECS) | Fargate cluster for Streamlit web app |

### 🔧 Jenkins Pipeline Features

The CI/CD pipeline provides flexible deployment options with built-in safety:

| Feature | Description |
|---------|-------------|
| **Deployment Types** | `NewDeployment`, `FullRelease`, `AgentRelease`, `AppRelease`, `UpdateInfra` |
| **Multi-Environment** | Deploy to `dev`, `staging`, or `prod` with a single parameter |
| **Parameterized Builds** | Agent name, version, region configurable per run |
| **Security Scanning** | Trivy scans for IaC and container vulnerabilities; Snyk for code |
| **Plan Before Apply** | Terraform plan with detailed exit codes; apply only on changes |
| **Approval Gates** | Manual approval required before infrastructure modifications |
| **Slack Integration** | Notifications for start, approval requests, success, and failure |
| **Selective Builds** | Build only agent, only app, or both based on deployment type |
| **Destroy Capability** | Safe teardown with plan preview and approval |

---

## 📸 Screenshots

### Pipeline Parameters

![Image](https://github.com/user-attachments/assets/2197e637-9415-4e06-9a72-aa7a06fc3d1f)

### Approval Gate

![Image](https://github.com/user-attachments/assets/68918f11-e0af-4b4e-b6fa-81cccc903e5f)

### Pipeline Stage Overview

![Image](https://github.com/user-attachments/assets/cddca19a-9a8b-4b23-9fb5-3a86890fd061)
![Image](https://github.com/user-attachments/assets/1b3eb405-f04d-47cf-ba0f-9a2d9546d039)

---

## 🐳 Running Locally

### Prerequisites

- Docker and Docker Compose installed
- AWS credentials configured (access key, secret key, or IAM role)
- AWS Bedrock model access enabled (Claude 4.5 Sonnet recommended)

### Quick Start with Docker Compose

1. **Clone the repository**
   ```bash
   git clone https://github.com/Tarique-B-DevOps/AWS-CloudOps-Agent.git
   cd AWS-CloudOps-Agent
   ```

2. **Configure environment variables**

   Required variables:
   ```
   AWS_ACCESS_KEY_ID=your_access_key
   AWS_SECRET_ACCESS_KEY=your_secret_key
   BEDROCK_MODEL_REGION=us-east-1
   BEDROCK_MODEL_ID=us.anthropic.claude-3-5-sonnet-20241022-v2:0
   ```

3. **Start the services**
   ```bash
   docker-compose up -d --build
   ```

4. **Access the application**
   - Web Interface: http://localhost:8501
   - API Health Check: http://localhost:8080/ping

5. **Stop the services**
   ```bash
   docker-compose down
   ```

### View Logs

```bash
docker-compose logs -f
```

---

## 📁 Project Structure

```
AWS-CloudOps-Agent/
├── agent.py              # FastAPI backend with Strands Agent
├── app.py                # Streamlit web interface
├── models.py             # Pydantic request/response schemas
├── Dockerfile.agent      # Agent container definition
├── Dockerfile.app        # Web app container definition
├── docker-compose.yml    # Local development orchestration
├── Jenkinsfile           # CI/CD pipeline definition
├── main.tf               # Root Terraform configuration
├── variables.tf          # Terraform variable definitions
├── outputs.tf            # Terraform output values
└── frontend/             # React/Vite frontend (under development)
```

---

## 📝 Notes

- **Least Privilege Principle**: The agent follows AWS security best practices. Grant only the specific permissions required for the operations you intend to perform. Avoid broad `*` permissions—scope IAM policies to the exact actions and resources the agent will access.

- **Model Access**: Ensure your AWS account has access to the Bedrock model specified in `BEDROCK_MODEL_ID`. Claude 3.5 Sonnet is recommended for optimal performance.


---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  <strong>Built with Strands Agent Framework • Deployed on AWS Bedrock AgentCore • Automated with Terraform & Jenkins</strong>
</p>
