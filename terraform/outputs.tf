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