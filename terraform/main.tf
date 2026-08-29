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
      max_instance_count = 1
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
    timeout         = "120s" # 2 minutes for AI evaluation jobs

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
          memory = "512Mi"
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
      max_instance_count = 1
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