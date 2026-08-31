# Step 3: Secrets & API Keys Setup

Step-by-step guide to generating application secrets, storing AI provider API keys in Secret Manager, and configuring access policies.

Back to: [docs/deployment/DEPLOYMENT_OPTIONS.md](docs/deployment/DEPLOYMENT_OPTIONS.md#rollout-checklist)

---

## 1. Generate and Store `JWT_SECRET`

Generate a 256-bit cryptographically secure secret for authentication token signing:

```bash
# Generate secret string
JWT_SECRET_VAL=$(openssl rand -base64 32)

# Create secret in Secret Manager
gcloud secrets create JWT_SECRET \
  --replication-policy="automatic"

# Add secret version
gcloud secrets versions add JWT_SECRET \
  --data-file=<(printf '%s' "${JWT_SECRET_VAL}")
```

---

## 2. Store AI Provider API Keys

Create a Secret Manager entry for the Google Gemini provider used by `inference`:

```bash
# Google Gemini API Key
gcloud secrets create GEMINI_API_KEY --replication-policy="automatic"
gcloud secrets versions add GEMINI_API_KEY \
  --data-file=<(printf '%s' "GEMINI_API_KEY")
```

---

## 3. Create Cloud Run Runtime Service Account & Grant Access

Cloud Run instances must assume a dedicated service account with `Secret Accessor` permissions to mount secrets as environment variables:

```bash
# Create runtime service account
gcloud iam service-accounts create exan-cloudrun-runtime \
  --display-name="Exan Cloud Run Runtime SA"

export RUNTIME_SA="exan-cloudrun-runtime@${PROJECT_ID}.iam.gserviceaccount.com"

# Grant Secret Manager Secret Accessor role on project level
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${RUNTIME_SA}" \
  --role="roles/secretmanager.secretAccessor"
```

---

## 4. Verify Secrets Configuration

List all registered secrets and confirm versions are active:

```bash
gcloud secrets list

# Test retrieving payload (example for JWT_SECRET)
gcloud secrets versions access latest --secret="JWT_SECRET"
```

---

## 5. Configure GitHub Actions Secrets for GCP Authentication

The steps above create secrets in **GCP Secret Manager**, which the deployed Cloud Run services read at runtime. Those are separate from the credentials the `deploy-cloud-run.yml` **GitHub Actions workflow** needs to authenticate to GCP *before* it can deploy anything. Storing secrets only in GCP is not enough — the workflow runs on GitHub's infrastructure and cannot access GCP until it authenticates, so at least one of the following must be added as a **GitHub repository secret** (Settings → Secrets and variables → Actions):

- **Workload Identity Federation (recommended, keyless)**: set both `GCP_WIF_PROVIDER` (the full workload identity provider resource name) and `GCP_WIF_SERVICE_ACCOUNT` (the service account email to impersonate). See [Workload Identity Federation](https://cloud.google.com/iam/docs/workload-identity-federation) and [`google-github-actions/auth`](https://github.com/google-github-actions/auth#workload-identity-federation-through-a-service-account) for how to create the provider and grant it impersonation rights.
- **Service account key (fallback)**: create a JSON key for a service account with the required deploy permissions and store its contents as `GCP_CREDENTIALS_JSON`.

If none of these secrets are set, the workflow fails fast with a clear error instead of attempting an invalid authentication call.

---

## Official Documentation & References

- [GCP Secret Manager Quickstart](https://cloud.google.com/secret-manager/docs/quickstart)
- [Secret Manager IAM Access Control](https://cloud.google.com/secret-manager/docs/access-control)
- [Mounting Secrets in Cloud Run](https://cloud.google.com/run/docs/configuring/secrets)
- [OpenAI API Keys](https://platform.openai.com/api-keys)
- [Anthropic API Keys](https://console.anthropic.com/settings/keys)
- [Google AI Studio (Gemini) API Keys](https://aistudio.google.com/app/apikey)
