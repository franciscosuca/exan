# Step 1: GCP Project & Foundation Setup

Step-by-step guide to initialize Google Cloud Platform (GCP) infrastructure prerequisites for Exan.

Back to: [docs/deployment/DEPLOYMENT_OPTIONS.md](docs/deployment/DEPLOYMENT_OPTIONS.md#rollout-checklist)

---

## 1. Create and Configure the GCP Project

```bash
# Set environment variables
export PROJECT_ID="exan-beta"
export REGION="europe-west1"

# Create GCP project
gcloud projects create ${PROJECT_ID} --name="Exan Platform"

# Set active project
gcloud config set project ${PROJECT_ID}

# Link billing account (find ACCOUNT_ID with: gcloud billing accounts list)
export BILLING_ACCOUNT_ID="YOUR_BILLING_ACCOUNT_ID"
gcloud billing projects link ${PROJECT_ID} --billing-account=${BILLING_ACCOUNT_ID}
```

---

## 2. Enable Required Google Cloud APIs

```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  storage.googleapis.com \
  iam.googleapis.com \
  iamcredentials.googleapis.com \
  cloudbuild.googleapis.com
```

---

## 3. Create Artifact Registry Repository

Create a standard Docker repository to store container images for `webapp`, `auth-server`, and `inference`:

```bash
gcloud artifacts repositories create exan-repo \
  --repository-format=docker \
  --location=${REGION} \
  --description="Docker repository for Exan container images"
```

Configure local Docker authentication for the registry:

```bash
gcloud auth configure-docker ${REGION}-docker.pkg.dev
```

---

## 4. Create Terraform State Storage Bucket

Create a Google Cloud Storage (GCS) bucket with Object Versioning enabled to store Terraform remote state securely:

```bash
export TF_STATE_BUCKET="tf-state-${PROJECT_ID}"

# Create bucket
gcloud storage buckets create gs://${TF_STATE_BUCKET} \
  --location=${REGION} \
  --uniform-bucket-level-access

# Enable versioning to protect state file history
gcloud storage buckets update gs://${TF_STATE_BUCKET} --versioning
```

---

## 5. Configure Workload Identity Federation for GitHub Actions (Optional / Recommended)

```bash
# Create service account for CI/CD deployments
gcloud iam service-accounts create github-actions \
  --display-name="GitHub Actions"

export SA_EMAIL="github-actions@${PROJECT_ID}.iam.gserviceaccount.com"

# Grant required roles for Cloud Run deployment and image pushing
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/iam.serviceAccountUser"
```

### 5a. Create the Workload Identity Pool and OIDC Provider

```bash
export PROJECT_NUMBER=$(gcloud projects describe ${PROJECT_ID} --format='value(projectNumber)')
export GITHUB_REPO="OWNER/REPO"   # e.g. "myuser/exan"

# Create the pool
gcloud iam workload-identity-pools create github-pool \
  --location=global \
  --display-name="GitHub Actions Pool"

# Create the OIDC provider that trusts GitHub's token issuer
gcloud iam workload-identity-pools providers create-oidc github-provider \
  --location=global \
  --workload-identity-pool=github-pool \
  --display-name="GitHub Provider" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
  --attribute-condition="assertion.repository=='${GITHUB_REPO}'"

# Allow tokens from this repository to impersonate the service account
gcloud iam service-accounts add-iam-policy-binding ${SA_EMAIL} \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-pool/attribute.repository/${GITHUB_REPO}"
```

### 5b. Register the GitHub Repository Secrets

In GitHub → Settings → Secrets and variables → Actions, add:

- `GCP_WIF_PROVIDER` — full provider resource name, printed by:

  ```bash
  echo "projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-pool/providers/github-provider"
  ```

- `GCP_WIF_SERVICE_ACCOUNT` — the service account email (`${SA_EMAIL}`).

### 5c. Fallback: Service Account Key (not recommended)

If Workload Identity Federation cannot be used, create a JSON key instead:

```bash
gcloud iam service-accounts keys create key.json --iam-account=${SA_EMAIL}
```

Store the **entire contents** of `key.json` as the GitHub secret `GCP_CREDENTIALS_JSON`, then delete the local file. The workflow uses WIF when both `GCP_WIF_*` secrets are set and falls back to this key otherwise. Keep the unused alternative unset.

---

## Official Documentation & References

- [Google Cloud Projects Guide](https://cloud.google.com/resource-manager/docs/creating-managing-projects)
- [Enabling GCP APIs](https://cloud.google.com/service-usage/docs/enable-disable)
- [Artifact Registry Docker Repositories](https://cloud.google.com/artifact-registry/docs/docker/store-docker-container-images)
- [Cloud Storage Bucket Versioning](https://cloud.google.com/storage/docs/object-versioning)
- [Workload Identity Federation for GitHub Actions](https://cloud.google.com/iam/docs/workload-identity-federation-with-deployment-pipelines)
