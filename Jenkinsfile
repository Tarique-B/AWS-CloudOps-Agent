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
                terraform init -no-color
                terraform validate -no-color
                """
            }
        }

        stage('Scan Terraform Config') {
            when {
                expression { return !params.destroy }
            }
            steps {
                script {
                    echo "🔍 Scanning Terraform configuration for HIGH/CRITICAL issues using Trivy..."

                    sh """
                    trivy config --severity HIGH,CRITICAL --format table .

                    # Count CRITICAL issues using jq
                    CRITICAL_COUNT=\$(trivy config --severity HIGH,CRITICAL --format json . \
                        | jq '[.Results[].Misconfigurations[]? | select(.Severity=="CRITICAL")] | length' || echo "0")

                    echo "⚠️ CRITICAL issues found: \$CRITICAL_COUNT"

                    if [ "\$CRITICAL_COUNT" -gt 5 ]; then
                        echo "Too many CRITICAL issues (>5). Failing pipeline."
                        exit 1
                    fi
                    """
                }
            }
        }

        stage('Create ECR Repositories') {
            when {
                expression { return !params.destroy }
            }
            steps {
                script {
                    echo "🔧 Creating/Ensuring ECR repositories exist..."
                    
                    echo "Running Terraform plan for ECR repositories..."
                    def ecrPlanExitCode = sh(
                        script: "terraform plan -no-color -target=module.ecr -detailed-exitcode -out=ecr-plan.out",
                        returnStatus: true
                    )
                    
                    if (ecrPlanExitCode == 0) {
                        echo "✅ No changes detected for ECR repositories. Skipping apply."
                    } else if (ecrPlanExitCode == 2) {
                        echo "⚠️ Changes detected for ECR repositories."
                        
                        slackSend color: "#FFD700", message: """
                        🛑 *Approval Required: ECR Repository Creation*
                        Job: ${env.JOB_NAME} #${env.BUILD_NUMBER} (<${env.BUILD_URL}console|Review>)
                        Environment: ${params.agentEnv}
                        Agent Name: ${params.agentName}
                        """
                        
                        input message: "⚡ Approve ECR repository creation?",
                            ok: "✅ Deploy",
                            submitter: "${env.APPROVER}"
                        
                        echo "Applying Terraform plan for ECR repositories..."
                        sh "terraform apply -no-color -auto-approve ecr-plan.out"
                    } else if (ecrPlanExitCode == 1) {
                        echo "❌ Terraform plan failed. Check logs above."
                        error "Terraform plan failed with exit code ${ecrPlanExitCode}"
                    } else {
                        echo "ℹ️ ECR repositories may not exist. Creating..."
                        
                        slackSend color: "#FFD700", message: """
                        🛑 *Approval Required: ECR Repository Creation*
                        Job: ${env.JOB_NAME} #${env.BUILD_NUMBER} (<${env.BUILD_URL}console|Review>)
                        Environment: ${params.agentEnv}
                        Agent Name: ${params.agentName}
                        """
                        
                        input message: "⚡ Approve ECR repository creation?",
                            ok: "✅ Deploy",
                            submitter: "${env.APPROVER}"
                        
                        sh "terraform apply -no-color -target=module.ecr -auto-approve"
                    }
                    
                    echo "📦 Getting ECR repository URLs from Terraform outputs..."
                    env.AGENT_ECR_REPO_URL = sh(
                        script: "terraform output -no-color -raw agent_ecr_repository_url",
                        returnStdout: true
                    ).trim()
                    
                    env.WEBAPP_ECR_REPO_URL = sh(
                        script: "terraform output -no-color -raw webapp_ecr_repository_url",
                        returnStdout: true
                    ).trim()
                    
                    echo "Agent ECR URL: ${env.AGENT_ECR_REPO_URL}"
                    echo "Webapp ECR URL: ${env.WEBAPP_ECR_REPO_URL}"
                }
            }
        }

        stage('Code Scan') {
            when {
                expression { return !params.destroy }
            }
            steps {
                script {
                    echo "🔍 Running code security scan..."
                    try {
                        withCredentials([string(credentialsId: 'snyk_token', variable: 'SNYK_TOKEN')]) {
                            sh """
                            echo "Running Snyk Code scan..."
                            snyk code test --severity-threshold=high || true
                            """
                        }
                    } catch (Exception e) {
                        echo "⚠️ Snyk code scan skipped (credentials not available or Snyk not installed). Continuing..."
                        echo "Consider setting up Snyk token credentials or installing Snyk CLI."
                    }
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
                        error "ECR repository URL not found. Please ensure ECR repository is created first."
                    }
                }
                echo "🐳 Building agent Docker image using buildx ..."
                sh """
                echo "📦 Logging into ECR repository: ${env.AGENT_ECR_REPO_URL}"
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
                        error "ECR repository URL not found. Please ensure ECR repository is created first."
                    }
                }
                echo "🐳 Building webapp Docker image using buildx..."
                sh """
                echo "📦 Logging into ECR repository: ${env.WEBAPP_ECR_REPO_URL}"
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
                expression { return !params.destroy }
            }
            steps {
                script {
                    echo "🔧 Deploying AgentCore Runtime and Memory..."

                    echo "Agent name: ${env.TF_VAR_agent_name}"
                    echo "Agent environment: ${env.TF_VAR_agent_env}"
                    echo "Agent version: ${env.TF_VAR_agent_version}"
                    echo "AWS region: ${env.TF_VAR_region}"
                    
                    echo "🔍 Running Terraform plan for AgentCore Runtime and Memory..."
                    def agentcorePlanExitCode = sh(
                        script: "terraform plan -no-color -target=module.agentcore_memory -target=module.agentcore_runtime -detailed-exitcode -out=agentcore-plan.out",
                        returnStatus: true
                    )
                    
                    if (agentcorePlanExitCode == 0) {
                        echo "✅ No changes detected for AgentCore Runtime and Memory. Skipping apply."
                    } else if (agentcorePlanExitCode == 2) {
                        echo "⚠️ Changes detected for AgentCore Runtime and Memory."
                        
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
                        
                        echo "Applying Terraform plan for AgentCore Runtime and Memory..."
                        sh "terraform apply -no-color -auto-approve agentcore-plan.out"
                    } else if (agentcorePlanExitCode == 1) {
                        echo "❌ Terraform plan failed. Check logs above."
                        error "Terraform plan failed with exit code ${agentcorePlanExitCode}"
                    } else {
                        echo "⚠️ Unexpected exit code: ${agentcorePlanExitCode}. Proceeding with approval request."
                        
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
                        
                        sh "terraform apply -no-color -auto-approve agentcore-plan.out"
                    }
                    
                    echo "✅ AgentCore Runtime and Memory deployment completed"
                }
            }
        }

        stage('Deploy Webapp') {
            when {
                expression { return !params.destroy }
            }
            steps {
                script {
                    echo "🔧 Deploying Webapp Resources (VPC, ALB, ECS)..."
                    
                    if (params.deploymentType == 'NewRelease') {
                        env.TF_VAR_force_new_deployment = "true"
                        echo "ℹ️ NewRelease detected. Setting force_new_deployment=true"
                    }
                    
                    echo "🔍 Running Terraform plan for Webapp Resources (VPC, ALB, ECS)..."
                    def webappPlanExitCode = sh(
                        script: "terraform plan -no-color -target=module.vpc -target=module.alb -target=module.ecs -detailed-exitcode -out=webapp-plan.out",
                        returnStatus: true
                    )
                    
                    if (webappPlanExitCode == 0) {
                        echo "✅ No changes detected for Webapp Resources. Skipping apply."
                    } else if (webappPlanExitCode == 2) {
                        echo "⚠️ Changes detected for Webapp Resources."
                        
                        slackSend color: "#FFD700", message: """
                        🛑 *Approval Required: Webapp Resources Deployment (VPC, ALB, ECS)*
                        Job: ${env.JOB_NAME} #${env.BUILD_NUMBER} (<${env.BUILD_URL}console|Review>)
                        Environment: ${params.agentEnv}
                        Agent Name: ${params.agentName}
                        Deployment Type: ${params.deploymentType}
                        """
                        
                        input message: "⚡ Approve Webapp Resources (VPC, ALB, ECS) deployment?",
                            ok: "✅ Deploy",
                            submitter: "${env.APPROVER}"
                        
                        echo "Applying Terraform plan for Webapp Resources..."
                        sh "terraform apply -no-color -auto-approve webapp-plan.out"
                    } else if (webappPlanExitCode == 1) {
                        echo "❌ Terraform plan failed. Check logs above."
                        error "Terraform plan failed with exit code ${webappPlanExitCode}"
                    } else {
                        echo "⚠️ Unexpected exit code: ${webappPlanExitCode}. Proceeding with approval request."
                        
                        slackSend color: "#FFD700", message: """
                        🛑 *Approval Required: Webapp Resources Deployment (VPC, ALB, ECS)*
                        Job: ${env.JOB_NAME} #${env.BUILD_NUMBER} (<${env.BUILD_URL}console|Review>)
                        Environment: ${params.agentEnv}
                        Agent Name: ${params.agentName}
                        Deployment Type: ${params.deploymentType}
                        """
                        
                        input message: "⚡ Approve Webapp Resources (VPC, ALB, ECS) deployment?",
                            ok: "✅ Deploy",
                            submitter: "${env.APPROVER}"
                        
                        sh "terraform apply -no-color -auto-approve webapp-plan.out"
                    }
                    
                    echo "✅ Webapp Resources deployment completed"
                }
            }
        }



        stage('Terraform Destroy') {
            when {
                expression { return params.destroy }
            }
            steps {
                script {
                    echo "⚠️ Destroy parameter is checked. Running Terraform destroy..."
                    
                    echo "🔧 Initializing Terraform to get ECR repository information..."
                    sh "terraform init -no-color"
                    
                    echo "📦 Extracting ECR repository URLs from Terraform outputs..."
                    try {
                        env.AGENT_ECR_REPO_URL = sh(
                            script: "terraform output -no-color -raw agent_ecr_repository_url 2>/dev/null || echo ''",
                            returnStdout: true
                        ).trim()
                        
                        env.WEBAPP_ECR_REPO_URL = sh(
                            script: "terraform output -no-color -raw webapp_ecr_repository_url 2>/dev/null || echo ''",
                            returnStdout: true
                        ).trim()
                        
                        echo "Agent ECR URL: ${env.AGENT_ECR_REPO_URL}"
                        echo "Webapp ECR URL: ${env.WEBAPP_ECR_REPO_URL}"
                    } catch (Exception e) {
                        echo "⚠️ Could not extract ECR repository URLs from Terraform outputs. Will try to delete images using repository names."
                    }
                    
                    input message: """
                    ⚠️ Are you sure you want to destroy all resources including:
                    • ECR images for agent and webapp repositories
                    • AgentCore Runtime
                    • VPC, ELB, and ECS resources
                    This action will permanently delete all associated resources.
                    """,
                    ok: "✅ Proceed",
                    submitter: "${env.APPROVER}"
                    
                    sh """
                    echo "🗑️ Deleting ECR images before destroying infrastructure..."
                    
                    # Function to extract repository name from ECR URL
                    extract_repo_name() {
                        local url=\$1
                        if [ -n "\$url" ]; then
                            # Extract repo name from URL (format: <account>.dkr.ecr.<region>.amazonaws.com/<repo-name>)
                            echo "\$url" | sed 's|.*/||'
                        fi
                    }
                    
                    # Function to delete all images from a repository
                    delete_repo_images() {
                        local repo_name=\$1
                        if [ -z "\$repo_name" ]; then
                            echo "ℹ Skipping empty repository name"
                            return
                        fi
                        
                        echo "Checking repository: \$repo_name"
                        if aws ecr describe-repositories --repository-names "\$repo_name" --region ${params.awsRegion} 2>/dev/null; then
                            echo "📋 Listing all images in repository: \$repo_name"
                            IMAGES=\$(aws ecr list-images --repository-name "\$repo_name" --query 'imageIds[*]' --output json --region ${params.awsRegion} 2>/dev/null || echo "[]")
                            
                            if [ "\$IMAGES" != "[]" ] && [ -n "\$IMAGES" ] && [ "\$IMAGES" != "null" ]; then
                                echo "🗑️ Deleting all images in repository: \$repo_name"
                                aws ecr batch-delete-image --repository-name "\$repo_name" --image-ids "\$IMAGES" --region ${params.awsRegion}
                                echo "✅ Deleted all images in \$repo_name"
                            else
                                echo "ℹ No images found in \$repo_name"
                            fi
                        else
                            echo "ℹ Repository \$repo_name does not exist or cannot be accessed"
                        fi
                    }
                    
                    # Delete images from agent repository
                    if [ -n "${env.AGENT_ECR_REPO_URL}" ]; then
                        AGENT_REPO_NAME=\$(extract_repo_name "${env.AGENT_ECR_REPO_URL}")
                        delete_repo_images "\$AGENT_REPO_NAME"
                    else
                        echo "⚠️ Agent ECR repository URL not found. Trying default repository name..."
                        delete_repo_images "${params.agentName}"
                    fi
                    
                    # Delete images from webapp repository
                    if [ -n "${env.WEBAPP_ECR_REPO_URL}" ]; then
                        WEBAPP_REPO_NAME=\$(extract_repo_name "${env.WEBAPP_ECR_REPO_URL}")
                        delete_repo_images "\$WEBAPP_REPO_NAME"
                    else
                        echo "⚠️ Webapp ECR repository URL not found. Trying default repository name..."
                        delete_repo_images "${params.agentName}_webapp"
                    fi
                    
                    echo "🔧 Proceeding with Terraform destroy..."
                    terraform destroy -no-color -auto-approve
                    """
                }
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
