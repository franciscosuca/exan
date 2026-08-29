# Step 5: Terraform Configuration

Step-by-step guide to provisioning the Google Cloud infrastructure (Artifact Registry, Cloud Run services, IAM bindings, and Secret references) using Terraform.

Before starting, read [Terraform Basics and macOS Setup](TERRAFORM_BASICS.md) for the Terraform workflow, installation, and Google Cloud authentication steps.

Back to: [docs/deployment/DEPLOYMENT_OPTIONS.md](docs/deployment/DEPLOYMENT_OPTIONS.md#rollout-checklist)

---

## 1. Terraform Project Directory Layout

Organize configuration files inside a root `terraform/` directory:

```text
terraform/
├── versions.tf        # Provider requirements & GCS backend configuration
├── variables.tf       # Input variable declarations
├── main.tf            # Core cloud resources (Artifact Registry, SA, Cloud Run)
├── outputs.tf         # Cloud Run service URLs and artifact endpoints
└── terraform.tfvars   # Environment-specific parameter values
```

---

## 2. Configuration Files

### `versions.tf`

```hcl
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.30"
    }
  }

  backend "gcs" {
    bucket = "tf-state-exan-beta"
    prefix = "terraform/state/beta"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}
```

### `variables.tf`

```hcl
variable "project_id" {
  type        = string
  description = "GCP Project ID"
}

variable "region" {
  type        = string
  description = "Primary GCP Region"
  default     = "europe-west1"
}

variable "repository_name" {
  type        = string
  description = "Artifact Registry Docker repository name"
  default     = "exan-repo"
}
```

### `main.tf`

```hcl
# 1. Import the Artifact Registry Repository created in Step 1
import {
  to = google_artifact_registry_repository.repo
  id = "projects/${var.project_id}/locations/${var.region}/repositories/${var.repository_name}"
}

# Keep this resource block after import so Terraform manages its configuration.
resource "google_artifact_registry_repository" "repo" {
  location      = var.region
  repository_id = var.repository_name
  description   = "Docker repository for Exan microservices"
  format        = "DOCKER"
}

# 2. Cloud Run Runtime Service Account
resource "google_service_account" "cloudrun_sa" {
  account_id   = "exan-cloudrun-runtime"
  display_name = "Exan Cloud Run Runtime Service Account"
}

# Grant Secret Manager Secret Accessor to Runtime SA
resource "google_project_iam_member" "secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.cloudrun_sa.email}"
}

# 3. Cloud Run: auth-server
resource "google_cloud_run_v2_service" "auth_server" {
  name     = "auth-server"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.cloudrun_sa.email

    scaling {
      min_instance_count = 0
      max_instance_count = 5
    }

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${var.repository_name}/auth-server:latest"

      ports {
        container_port = 3001
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }

      env {
        name  = "PORT"
        value = "3001"
      }

      env {
        name = "JWT_SECRET"
        value_source {
          secret_key_ref {
            secret  = "JWT_SECRET"
            version = "latest"
          }
        }
      }

      env {
        name = "MONGO_URI"
        value_source {
          secret_key_ref {
            secret  = "MONGO_URI"
            version = "latest"
          }
        }
      }
    }
  }
}

# 4. Cloud Run: inference
resource "google_cloud_run_v2_service" "inference" {
  name     = "inference"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.cloudrun_sa.email
    timeout         = "3600s" # 60 minutes for AI evaluation jobs

    scaling {
      min_instance_count = 0
      max_instance_count = 1 # Pinned to 1 instance for in-memory workflow state
    }

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${var.repository_name}/inference:latest"

      ports {
        container_port = 8000
      }

      resources {
        limits = {
          cpu    = "2"
          memory = "2Gi"
        }
      }

      env {
        name = "JWT_SECRET"
        value_source {
          secret_key_ref {
            secret  = "JWT_SECRET"
            version = "latest"
          }
        }
      }

      env {
        name = "OPENAI_API_KEY"
        value_source {
          secret_key_ref {
            secret  = "OPENAI_API_KEY"
            version = "latest"
          }
        }
      }

      env {
        name = "ANTHROPIC_API_KEY"
        value_source {
          secret_key_ref {
            secret  = "ANTHROPIC_API_KEY"
            version = "latest"
          }
        }
      }

      env {
        name = "GEMINI_API_KEY"
        value_source {
          secret_key_ref {
            secret  = "GEMINI_API_KEY"
            version = "latest"
          }
        }
      }
    }
  }
}

# 5. Cloud Run: webapp
resource "google_cloud_run_v2_service" "webapp" {
  name     = "webapp"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.cloudrun_sa.email

    scaling {
      min_instance_count = 0
      max_instance_count = 10
    }

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${var.repository_name}/webapp:latest"

      ports {
        container_port = 80
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }
    }
  }
}

# 6. IAM Public Invocations
resource "google_cloud_run_service_iam_member" "public_webapp" {
  location = google_cloud_run_v2_service.webapp.location
  service  = google_cloud_run_v2_service.webapp.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_service_iam_member" "public_auth" {
  location = google_cloud_run_v2_service.auth_server.location
  service  = google_cloud_run_v2_service.auth_server.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_service_iam_member" "public_inference" {
  location = google_cloud_run_v2_service.inference.location
  service  = google_cloud_run_v2_service.inference.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
```

### `outputs.tf`

```hcl
output "webapp_url" {
  value       = google_cloud_run_v2_service.webapp.uri
  description = "Public URL for webapp service"
}

output "auth_server_url" {
  value       = google_cloud_run_v2_service.auth_server.uri
  description = "Public URL for auth-server service"
}

output "inference_url" {
  value       = google_cloud_run_v2_service.inference.uri
  description = "Public URL for inference service"
}

output "artifact_registry_repo" {
  value       = google_artifact_registry_repository.repo.name
  description = "Artifact Registry Docker repository identifier"
}
```

---

## 3. Initialization and Application

```bash
cd terraform

# Initialize providers and GCS state backend
terraform init

# Validate configuration
terraform validate

# Review execution plan; it includes importing the existing repository.
terraform plan -var="project_id=YOUR_PROJECT_ID" -var="region=us-central1"

# Import the existing repository and provision the remaining resources.
terraform apply -var="project_id=YOUR_PROJECT_ID" -var="region=us-central1"
```

---

## Official Documentation & References

- [Terraform Google Provider Documentation](https://registry.terraform.io/providers/hashicorp/google/latest/docs)
- [google_cloud_run_v2_service Resource](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/cloud_run_v2_service)
- [google_artifact_registry_repository Resource](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/artifact_registry_repository)
- [Terraform GCS Backend Documentation](https://developer.hashicorp.com/terraform/language/settings/backends/gcs)
