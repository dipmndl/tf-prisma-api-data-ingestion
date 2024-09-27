# TF-Prisma-API-Data-Ingestion

The `tf-prisma-api-data-ingestion` project automates the process of ingesting data from Prisma Cloud APIs into an AWS S3 bucket through AWS Lambda functions. This project uses Terraform to provision and manage the AWS resources required for this workflow, ensuring that infrastructure is reproducibly created and managed as code.

## Project Structure

This repository is organized as follows:
    /tf-prisma-api-data-ingestion
    │
    ├── .gitignore # Specifies intentionally untracked files to ignore
    ├── README.md # This documentation file
    │
    ├── terraform/ # Contains Terraform configurations and modules
    │ ├── modules/ # Terraform modules for Lambda functions and more
    │ │ ├── lambda_function_1/
    │ │ └── lambda_function_2/
    │ ├── environments/ # Environment-specific Terraform configurations
    │ │ ├── dev/
    │ │ └── prod/
    │ └── global/ # Global configurations
    │
    └── src/ # Source code for Lambda functions
    ├── lambda_function_1/
    │ └── lambda_function.py
    ├── lambda_function_2/
    │ └── lambda_function.py
    └── requirements.txt # Shared Python dependencies for Lambda functions

## Prerequisites

Before deploying this project, ensure you have:

- An AWS account with necessary permissions to create Lambda functions, S3 buckets, and IAM roles.
- Terraform installed on your machine. [Download Terraform](https://www.terraform.io/downloads.html)
- Python installed, if you intend to modify or deploy the Lambda function code.

## Getting Started

    ### 1. Clone the Repository

    Start by cloning this repository to your local machine:

    git clone https://example.com/tf-prisma-api-data-ingestion.git
    cd tf-prisma-api-data-ingestion

    ### 2. Configure your AWS and Prisma Cloud API Access
    Ensure your AWS credentials are correctly configured on your machine.
    Store your Prisma Cloud API keys securely and ensure they're accessible to your Lambda functions as environment variables, following best practices for secret management.

    ### 3. Initialize Terraform
    Navigate to the Terraform environment configuration for your target deployment environment:
    cd terraform/environments/dev
    terraform init

    Repeat this step for any other environments as needed.

    ### 4. Deploy the Infrastructure
    Apply the Terraform configuration to provision the AWS resources:
    terraform apply

    ### 5. Verify Deployment
    Once the deployment is successful, verify that the Lambda functions are correctly set up and scheduled to run (if using events like CloudWatch to trigger executions). You can manually invoke the Lambda function to ensure it's operational:
    aws lambda invoke --function-name my-function-name response.json

## Cleaning Up
To avoid incurring unnecessary charges, remove the provisioned resources when they're no longer needed:

terraform destroy

## Contributing
Contributions to improve tf-prisma-api-data-ingestion are welcome. Please consider following the established workflows for feature addition or bug fixes:

Fork the repository.
Create a new feature branch.
Commit your changes.
Push to the branch.
Create a Pull Request.