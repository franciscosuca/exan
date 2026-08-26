# Terraform Basics and macOS Setup

A short introduction to Terraform before following [Step 5: Terraform Configuration](STEP_5_TERRAFORM_CONFIGURATION.md).

## What Terraform Does

Terraform is an **infrastructure as code** tool. Instead of creating cloud resources manually in the Google Cloud Console, you describe the desired infrastructure in `.tf` files. Terraform compares that description with the current Google Cloud environment and proposes the smallest set of changes needed.

The usual workflow is:

```text
Write configuration -> terraform plan -> review -> terraform apply
```

Terraform uses a **provider** to communicate with a platform. Exan uses the Google provider, which translates resources such as Cloud Run services, Artifact Registry repositories, service accounts, and IAM bindings into Google Cloud API operations.

Terraform also keeps **state**: a record of which real cloud resources belong to the configuration. Exan stores this state in a Google Cloud Storage (GCS) bucket so it can be shared and recovered. The state is not application data, and it should not be committed to Git.

Terraform provisions infrastructure; it does not build Docker images or run the application code. The referenced images must already exist in Artifact Registry before Cloud Run can start them.

## How Exan's Files Fit Together

| File | Purpose |
| ------ | --------- |
| `versions.tf` | Pins Terraform and provider versions, configures the GCS state backend, and selects the Google Cloud project and region. |
| `variables.tf` | Declares inputs such as `project_id`, `region`, and `repository_name`. |
| `main.tf` | Describes the Artifact Registry repository, Cloud Run services, service account, secrets, and IAM bindings. |
| `outputs.tf` | Prints useful values such as the deployed service URLs. |
| `terraform.tfvars` | Supplies environment-specific input values. Keep credentials and secret values out of this file. |

For example, this resource block identifies one managed Cloud Run service:

```hcl
resource "google_cloud_run_v2_service" "inference" {
  name     = "inference"
  location = var.region
}
```

The first label selects the Google resource type. The second label is Terraform's local name for that resource. The `name` attribute is the actual Cloud Run service name.

The `import` block in Exan's `main.tf` tells Terraform to begin managing the Artifact Registry repository that was created earlier by the GCP setup steps.

## Install Terraform on macOS

### 1. Install Homebrew

If Homebrew is not installed, follow the instructions at [brew.sh](https://brew.sh/). Then install Terraform from HashiCorp's Homebrew tap:

```bash
brew tap hashicorp/tap
brew install hashicorp/tap/terraform
terraform version
```

The last command should print the installed Terraform version.

### 2. Install the Google Cloud CLI

The CLI is useful for selecting a project and creating the Application Default Credentials that Terraform uses:

```bash
brew install --cask gcloud-cli
gcloud init
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

`gcloud init` configures the CLI account and defaults. `gcloud auth application-default login` authorizes local tools, including Terraform, to call Google Cloud APIs. Use an account with permission to manage the resources in this deployment.

Verify both tools are available:

```bash
terraform version
gcloud version
```

## Run Exan's Terraform Configuration

Before initialization, make sure the GCS state bucket from [Step 1: GCP Project Setup](STEP_1_GCP_PROJECT_SETUP.md) exists and that the Artifact Registry repository has been created. From the repository root:

```bash
cd terraform

terraform init

terraform fmt -check
terraform validate

terraform plan \
  -var="project_id=YOUR_PROJECT_ID" \
  -var="region=us-central1"

terraform apply \
  -var="project_id=YOUR_PROJECT_ID" \
  -var="region=us-central1"
```

You can put the same non-secret values in `terraform.tfvars` instead:

```hcl
project_id      = "YOUR_PROJECT_ID"
region          = "us-central1"
repository_name = "exan-repo"
```

Then `terraform plan` and `terraform apply` will load them automatically. Always read the plan carefully: `apply` can create billable resources, change IAM access, or replace existing resources.

## Command Summary

| Command | What it does |
| --------- | -------------- |
| `terraform init` | Installs providers and connects the configured backend. Run again when backend or provider requirements change. |
| `terraform fmt` | Formats Terraform files consistently. |
| `terraform validate` | Checks syntax and internal configuration references. |
| `terraform plan` | Previews changes without applying them. |
| `terraform apply` | Applies the reviewed changes to Google Cloud. |
| `terraform output` | Displays values declared in `outputs.tf`, such as service URLs. |

For the complete Exan resource configuration, continue with [Step 5: Terraform Configuration](STEP_5_TERRAFORM_CONFIGURATION.md).
