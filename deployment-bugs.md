# Deployment Issues & Bugs

Summary of deployment and workflow issues identified in the Google Cloud Run deployment pipeline for Exan.

---

### 1. Flexible GCP Authentication Inputs (WIF or Service Account Key) ✅
- **Area**: CI/CD (`.github/workflows/deploy-cloud-run.yml`)
- **Problem**: `google-github-actions/auth@v2` requires exactly one authentication method. Supplying both `workload_identity_provider` and `credentials_json`, or providing neither, causes a fatal error.
- **Solution**: Prefer Workload Identity Federation (WIF) when `GCP_WIF_PROVIDER` and `GCP_WIF_SERVICE_ACCOUNT` secrets are set; otherwise fall back to `credentials_json` via the `GCP_CREDENTIALS_JSON` secret, but only when it is present. A precheck step now fails fast with a clear error message if neither authentication method is configured, instead of calling `google-github-actions/auth@v2` with an empty `credentials_json`. See [STEP_3_SECRETS_SETUP.md](docs/deployment/STEP_3_SECRETS_SETUP.md#5-configure-github-actions-secrets-for-gcp-authentication) for how to set these as GitHub Actions secrets.
- **Status**: **Resolved** in [deploy-cloud-run.yml](.github/workflows/deploy-cloud-run.yml).

---

### 2. Missing Optional Secrets in GCP Secret Manager ✅
- **Area**: CI/CD & GCP Secret Manager (`.github/workflows/deploy-cloud-run.yml`)
- **Problem**: `gcloud run deploy inference` attempted to bind `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` via `--set-secrets`. If those secrets are not created in GCP Secret Manager, the deployment fails immediately.
- **Solution**: Scoped `--set-secrets` to only active secrets (`JWT_SECRET` and `GEMINI_API_KEY`) as documented in [STEP_3_SECRETS_SETUP.md](docs/deployment/STEP_3_SECRETS_SETUP.md) and [cloudbuild.yaml](docs/deployment/cloudbuild.yaml).
- **Status**: **Resolved** in [deploy-cloud-run.yml](.github/workflows/deploy-cloud-run.yml).

---

### 3. Missing Cloud Run Runtime Service Account in Deploy Commands ✅
- **Area**: CI/CD (`.github/workflows/deploy-cloud-run.yml`)
- **Problem**: `gcloud run deploy` commands omit the `--service-account` flag. When omitted, Cloud Run defaults to the default Compute Engine service account (`<project-number>-compute@developer.gserviceaccount.com`), which lacks `roles/secretmanager.secretAccessor` permissions to access Secret Manager secrets at runtime.
- **Solution**: Add `--service-account exan-cloudrun-runtime@${{ env.PROJECT_ID }}.iam.gserviceaccount.com` to each `gcloud run deploy` step.
- **Status**: **Resolved** in [deploy-cloud-run.yml](.github/workflows/deploy-cloud-run.yml).

---

### 4. Nginx Reverse Proxy Upstream Resolution on Cloud Run ✅
- **Area**: Webapp Container (`webapp/nginx.conf`)
- **Problem**: A static nginx configuration cannot use Compose-only hostnames in Cloud Run. Hard-coded placeholder URLs are also not substituted automatically, and HTTPS Cloud Run upstreams require the upstream Host header and SNI.
- **Solution**: `webapp/nginx.conf` is now rendered at container startup from `AUTH_SERVER_URL` and `INFERENCE_SERVER_URL`. Compose sets those values to `http://auth-server:3001` and `http://inference:8000`; the deployment workflow and Terraform set them to the actual Cloud Run service URIs. The rendered configuration uses the upstream Host header, TLS SNI, and a proxy timeout longer than the inference service timeout. Since the template renders literal upstreams before nginx starts, normal startup DNS resolution is sufficient and a variable-based nginx `resolver` is not required.
- **Status**: **Resolved** in [nginx.conf](webapp/nginx.conf), [nginx-entrypoint.sh](webapp/nginx-entrypoint.sh), [docker-compose.yml](docker-compose.yml), [deploy-cloud-run.yml](.github/workflows/deploy-cloud-run.yml), and [main.tf](terraform/main.tf).

---

### 5. Malformed Artifact Registry URLs on Missing Secret
- **Area**: CI/CD (`.github/workflows/deploy-cloud-run.yml`)
- **Problem**: `PROJECT_ID: ${{ secrets.GCP_PROJECT_ID }}` caused image paths to become `europe-west1-docker.pkg.dev//exan-repo/...` if the secret was unset in GitHub Actions.
- **Solution**: Set explicit default `PROJECT_ID: 'exan-beta'` in the workflow `env`.
- **Status**: **Resolved** in [deploy-cloud-run.yml](.github/workflows/deploy-cloud-run.yml).

---

### 6. Redundant Test Suite Execution in Deployment Workflow ✅
- **Area**: CI/CD (`.github/workflows/deploy-cloud-run.yml`)
- **Problem**: The `test` job in `deploy-cloud-run.yml` duplicates the testing performed by [test-pipeline.yml](.github/workflows/test-pipeline.yml) on pull requests, adding build latency to production releases.
- **Solution**: Remove the `test` job and the `needs: test` dependency from `build-and-deploy` in `deploy-cloud-run.yml`.
- **Status**: **Resolved** in [deploy-cloud-run.yml](.github/workflows/deploy-cloud-run.yml).
