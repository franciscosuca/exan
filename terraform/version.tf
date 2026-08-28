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