variable "project_id" {
  type        = string
  description = "exan-beta"
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