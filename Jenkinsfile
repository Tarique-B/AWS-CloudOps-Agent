pipeline {
    agent { label 'AI-ML-RTX-NODE' }

    parameters {
        choice(
            name: 'deploymentType',
            choices: ['NewDeployment', 'NewRelease'],
            description: 'Deployment type: NewDeployment creates all resources, NewRelease only builds/pushes new images'
        )
        string(
            name: 'agentName', 
            defaultValue: 'cloudops_agent', 
            description: 'Name of the agent (used for resource naming)'
        )
        choice(
            name: 'agentEnv',
            choices: ['dev', 'staging', 'prod'],
            description: 'Target environment for deployment'
        )
        string(
            name: 'agentVersion', 
            defaultValue: 'v2.0.0', 
            description: 'Version of the agent to deploy'
        )
        string(
            name: 'awsRegion', 
            defaultValue: 'us-east-1', 
            description: 'The AWS region to deploy resources in'
        )
        booleanParam(
            name: 'destroy', 
            defaultValue: false, 
            description: 'If checked, only run terraform destroy'
        )
    }

    environment {
        AWS_ACCESS_KEY_ID         = credentials('aws-access-key')
        AWS_SECRET_ACCESS_KEY     = credentials('aws-secret-key')
        AWS_DEFAULT_REGION        = "${params.awsRegion}"
        TF_TOKEN_app_terraform_io = credentials('terraform-cloud-token')
        TF_VAR_agent_name         = "${params.agentName}"
        TF_VAR_agent_env          = "${params.agentEnv}"
        TF_VAR_agent_version      = "${params.agentVersion}"
        TF_VAR_region             = "${params.awsRegion}"
        IMAGE_LATEST              = "latest"
        AGENT_NAME                = "${params.agentName}"
        AGENT_ENV                 = "${params.agentEnv}"
        AGENT_VERSION             = "${params.agentVersion}"
        DEPLOYMENT_TYPE           = "${params.deploymentType}"
        NAME_PREFIX               = "${params.agentName}_${params.agentEnv}"
        JOB_TYPE                  = "${params.destroy ? 'Destroy' : 'Deployment'}"
        APPROVER                  = "tarique"
    }

    stages {

        stage('Notify Start') {
            steps {
                slackSend color: "#FFFF00", message: """
                🔔 CloudOps Agent Pipeline Started
                Job Type: ${env.JOB_TYPE}
                Deployment Type: ${params.deploymentType}
                Job: ${env.JOB_NAME} #${env.BUILD_NUMBER} (<${env.BUILD_URL}console|Open>)
                Environment: ${params.agentEnv}
                Agent Name: ${params.agentName}
                Agent Version: ${env.AGENT_VERSION}
                """
            }
        }

        stage('Terraform Init & Validate') {
            when {
                expression { return !params.destroy }
            }
            steps {
                echo "🔍 Initializing and validating Terraform configuration..."
                sh """
                terraform init
                terraform validate
                """
            }
        }

        stage('Create ECR Repositories') {
            when {
                expression { return !params.destroy }
            }
            steps {
                script {
                    echo "🔧 Creating/Ensuring ECR repositories exist..."
                    
                    echo "Initializing Terraform..."
                    sh """
                    terraform init
                    """
                    
                    echo "Creating ECR repositories (will use existing if already present)..."
                    sh """
                    terraform apply -target=module.ecr -auto-approve
                    """
                    
                    echo "📦 Getting ECR repository URLs from Terraform outputs..."
                    env.AGENT_ECR_REPO_URL = sh(
                        script: "terraform output -raw agent_ecr_repository_url",
                        returnStdout: true
                    ).trim()
                    
                    env.WEBAPP_ECR_REPO_URL = sh(
                        script: "terraform output -raw webapp_ecr_repository_url",
                        returnStdout: true
                    ).trim()
                    
                    echo "Agent ECR URL: ${env.AGENT_ECR_REPO_URL}"
                    echo "Webapp ECR URL: ${env.WEBAPP_ECR_REPO_URL}"
                }
            }
        }

        stage('Build Agent Docker Image') {
            when {
                expression { return !params.destroy }
            }
            steps {
                script {
                    if (!env.AGENT_ECR_REPO_URL || env.AGENT_ECR_REPO_URL.isEmpty()) {
                        echo "📦 Getting ECR repository URL..."
                        env.AGENT_ECR_REPO_URL = sh(
                            script: "terraform output -raw ecr_repository_url 2>/dev/null || aws ecr describe-repositories --repository-names ${NAME_PREFIX} --query 'repositories[0].repositoryUri' --output text --region ${params.awsRegion}",
                            returnStdout: true
                        ).trim()
                    }
                    
                    if (!env.AGENT_ECR_REPO_URL || env.AGENT_ECR_REPO_URL.isEmpty()) {
                        error "ECR repository URL not found. Please ensure ECR repository is created first."
                    }
                }
                echo "🐳 Building agent Docker image using buildx ..."
                sh """
                aws ecr get-login-password --region ${params.awsRegion} | \
                    docker login --username AWS --password-stdin ${env.AGENT_ECR_REPO_URL}

                echo "Setting up Docker buildx..."
                docker buildx create --use --name multiarch-builder || true
                docker buildx inspect --bootstrap || true

                echo "Building agent Docker image for ${AGENT_VERSION}..."
                docker buildx build \
                    --platform linux/arm64 \
                    --load \
                    -f Dockerfile.agent \
                    -t ${env.AGENT_ECR_REPO_URL}:${AGENT_VERSION} \
                    -t ${env.AGENT_ECR_REPO_URL}:${IMAGE_LATEST} \
                    .
                """
            }
        }

        stage('Scan Agent Image') {
            when {
                expression { return !params.destroy }
            }
            steps {
                echo "🔍 Scanning agent Docker image for vulnerabilities..."
                sh """
                VULN_COUNT_AGENT=\$(trivy image --severity HIGH,CRITICAL --format json ${env.AGENT_ECR_REPO_URL}:${AGENT_VERSION} \
                    | jq '[.Results[].Vulnerabilities[]? | select(.Severity=="CRITICAL")] | length' || echo "0")

                echo "⚠️ Number of CRITICAL vulnerabilities in agent image: \$VULN_COUNT_AGENT"

                if [ "\$VULN_COUNT_AGENT" -gt 5 ]; then
                    echo "Agent container image has too many CRITICAL vulnerabilities. Failing pipeline."
                    exit 1
                fi
                """
            }
        }

        stage('Push Agent Docker Image') {
            when {
                expression { return !params.destroy }
            }
            steps {
                echo "📤 Pushing agent Docker images to ECR..."
                sh """
                docker push ${env.AGENT_ECR_REPO_URL}:${AGENT_VERSION}
                docker push ${env.AGENT_ECR_REPO_URL}:${IMAGE_LATEST}
                """
            }
        }

        stage('Build Webapp Docker Image') {
            when {
                expression { return !params.destroy }
            }
            steps {
                script {
                    if (!env.WEBAPP_ECR_REPO_URL || env.WEBAPP_ECR_REPO_URL.isEmpty()) {
                        echo "📦 Getting Webapp ECR repository URL..."
                        env.WEBAPP_ECR_REPO_URL = sh(
                            script: "terraform output -raw webapp_ecr_repository_url",
                            returnStdout: true
                        ).trim()
                    }
                }
                echo "🐳 Building webapp Docker image using buildx (ARM architecture)..."
                sh """
                aws ecr get-login-password --region ${params.awsRegion} | \
                    docker login --username AWS --password-stdin ${env.WEBAPP_ECR_REPO_URL}

                echo "Setting up Docker buildx..."
                docker buildx create --use --name multiarch-builder || true
                docker buildx inspect --bootstrap || true

                echo "Building webapp Docker image for ${AGENT_VERSION}..."
                docker buildx build \
                    --platform linux/arm64 \
                    --load \
                    -f Dockerfile.app \
                    -t ${env.WEBAPP_ECR_REPO_URL}:${AGENT_VERSION} \
                    -t ${env.WEBAPP_ECR_REPO_URL}:${IMAGE_LATEST} \
                    .
                """
            }
        }

        stage('Scan Webapp Image') {
            when {
                expression { return !params.destroy }
            }
            steps {
                echo "🔍 Scanning webapp Docker image for vulnerabilities..."
                sh """
                VULN_COUNT_WEBAPP=\$(trivy image --severity HIGH,CRITICAL --format json ${env.WEBAPP_ECR_REPO_URL}:${AGENT_VERSION} \
                    | jq '[.Results[].Vulnerabilities[]? | select(.Severity=="CRITICAL")] | length' || echo "0")

                echo "⚠️ Number of CRITICAL vulnerabilities in webapp image: \$VULN_COUNT_WEBAPP"

                if [ "\$VULN_COUNT_WEBAPP" -gt 5 ]; then
                    echo "Webapp container image has too many CRITICAL vulnerabilities. Failing pipeline."
                    exit 1
                fi
                """
            }
        }

        stage('Push Webapp Docker Image') {
            when {
                expression { return !params.destroy }
            }
            steps {
                echo "📤 Pushing webapp Docker images to ECR..."
                sh """
                docker push ${env.WEBAPP_ECR_REPO_URL}:${AGENT_VERSION}
                docker push ${env.WEBAPP_ECR_REPO_URL}:${IMAGE_LATEST}
                """
            }
        }

        stage('Deploy AgentCore Runtime and Memory') {
            when {
                expression { return !params.destroy && params.deploymentType == 'NewDeployment' }
            }
            steps {
                script {
                    echo "🔧 Deploying AgentCore Runtime and Memory..."

                    echo "Agent name: ${env.TF_VAR_agent_name}"
                    echo "Agent environment: ${env.TF_VAR_agent_env}"
                    echo "Agent version: ${env.TF_VAR_agent_version}"
                    echo "AWS region: ${env.TF_VAR_region}"
                    
                    slackSend color: "#FFD700", message: """
                    🛑 *Approval Required: AgentCore Runtime and Memory Deployment*
                    Job: ${env.JOB_NAME} #${env.BUILD_NUMBER} (<${env.BUILD_URL}console|Review>)
                    Environment: ${params.agentEnv}
                    Agent Name: ${params.agentName}
                    Agent Image: ${env.AGENT_ECR_REPO_URL}:${AGENT_VERSION}
                    """
                    
                    input message: "⚡ Approve AgentCore Runtime and Memory deployment?",
                        ok: "✅ Deploy",
                        submitter: "${env.APPROVER}"
                    

                    echo "Step 1: Deploying AgentCore Memory..."
                    sh """
                    terraform apply -target=module.agentcore_memory -auto-approve
                    """
                    
                    echo "Step 2: Deploying AgentCore Runtime..."
                    sh """
                    terraform apply -target=module.agentcore_runtime -auto-approve
                    """
                    
                    echo "✅ AgentCore Runtime and Memory deployment completed"
                }
            }
        }

        stage('Deploy Webapp Resources') {
            when {
                expression { return !params.destroy && params.deploymentType == 'NewDeployment' }
            }
            steps {
                script {
                    echo "🔧 Deploying Webapp Resources (VPC, ALB, ECS)..."
                    
                    slackSend color: "#FFD700", message: """
                    🛑 *Approval Required: Webapp Resources Deployment*
                    Job: ${env.JOB_NAME} #${env.BUILD_NUMBER} (<${env.BUILD_URL}console|Review>)
                    Environment: ${params.agentEnv}
                    Agent Name: ${params.agentName}
                    Webapp Image: ${env.WEBAPP_ECR_REPO_URL}:${AGENT_ENV}
                    This will deploy: VPC, ALB, ECS
                    """
                    
                    input message: "⚡ Approve Webapp Resources deployment?",
                        ok: "✅ Deploy",
                        submitter: "${env.APPROVER}"
                    
                    echo "Step 1: Deploying VPC..."
                    sh """
                    terraform apply -target=module.vpc -auto-approve
                    """
                    
                    echo "Step 2: Deploying ALB..."
                    sh """
                    terraform apply -target=module.alb -auto-approve
                    """
                    
                    echo "Step 3: Deploying ECS Cluster..."
                    sh """
                    terraform apply -target=module.ecs -auto-approve
                    """
                    
                    echo "✅ Webapp Resources deployment completed"
                }
            }
        }


        stage('Terraform Destroy') {
            when {
                expression { return params.destroy }
            }
            steps {
                echo "⚠️ Destroy parameter is checked. Running Terraform destroy..."
                
                input message: """
                ⚠️ Are you sure you want to destroy all resources including:
                • ECR images for ${AGENT_NAME} and ${AGENT_NAME}_frontend
                • AgentCore Runtime
                • VPC, ELB, and ECS resources
                This action will permanently delete all associated resources.
                """,
                ok: "✅ Proceed",
                submitter: "${env.APPROVER}"
                
                sh """
                echo "Deleting all ECR images for repositories: CloudOps_Agent and CloudOps_Agent_Webapp"
                
                for REPO in CloudOps_Agent CloudOps_Agent_Webapp; do
                    echo "Checking repository: \$REPO"
                    if aws ecr describe-repositories --repository-names \$REPO --region ${params.awsRegion} 2>/dev/null; then
                        echo "Deleting all images in repository: \$REPO"
                        IMAGES=\$(aws ecr list-images --repository-name \$REPO --query 'imageIds[*]' --output json --region ${params.awsRegion})
                        
                        if [ "\$IMAGES" != "[]" ] && [ -n "\$IMAGES" ]; then
                            aws ecr batch-delete-image --repository-name \$REPO --image-ids "\$IMAGES" --region ${params.awsRegion}
                            echo "✅ Deleted all images in \$REPO"
                        else
                            echo "ℹ No images found in \$REPO"
                        fi
                    else
                        echo "ℹ Repository \$REPO does not exist"
                    fi
                done
                
                echo "🔧 Proceeding with Terraform destroy..."
                terraform init
                terraform destroy -auto-approve
                """
            }
        }
    }

    post {
        success {
            slackSend color: "#00FF00", message: """
            ✅ CloudOps Agent Pipeline Succeeded
            Job Type: ${env.JOB_TYPE}
            Job: ${env.JOB_NAME} #${env.BUILD_NUMBER} (<${env.BUILD_URL}console|Open>)
            Environment: ${params.agentEnv}
            Agent Name: ${params.agentName}
            Agent Version: ${env.AGENT_VERSION}
            Agent ECR: ${env.AGENT_ECR_REPO_URL}
            Frontend ECR: ${env.FRONTEND_ECR_REPO_URL}
            """
        }
        failure {
            slackSend failOnError: true, color: "#FF0000", message: """
            ❌ CloudOps Agent Pipeline Failed
            Job Type: ${env.JOB_TYPE}
            Job: ${env.JOB_NAME} #${env.BUILD_NUMBER} (<${env.BUILD_URL}console|Open>)
            Environment: ${params.agentEnv}
            Agent Name: ${params.agentName}
            Agent Version: ${env.AGENT_VERSION}
            Check console logs for details: <${env.BUILD_URL}console|Open>
            """
        }
        unstable {
            slackSend color: "#FFA500", message: """
            ⚠️ CloudOps Agent Pipeline Unstable
            Job Type: ${env.JOB_TYPE}
            Job: ${env.JOB_NAME} #${env.BUILD_NUMBER} (<${env.BUILD_URL}console|Open>)
            Environment: ${params.agentEnv}
            Agent Name: ${params.agentName}
            Agent Version: ${env.AGENT_VERSION}
            """
        }
        always {
            echo "📌 Pipeline completed. Slack notifications sent."
        }
    }
}
