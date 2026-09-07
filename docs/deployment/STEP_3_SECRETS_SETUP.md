# Step 3: Secrets & API Keys Setup

Step-by-step guide to generating application secrets, storing AI provider API keys in Secret Manager, and configuring access policies.

Secret values are created outside Terraform. Terraform reads the existing Secret Manager entries and configures access for the Cloud Run runtime accounts without storing secret values in Terraform state or Git.

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

## 2. Store `MONGO_URI`

Create a Secret Manager entry for the MongoDB Atlas connection string used by `auth-server`:

```bash
# Replace the value with the connection string for this environment.
MONGO_URI_VAL='mongodb+srv://USER:PASSWORD@CLUSTER.mongodb.net/exan?retryWrites=true&w=majority'

gcloud secrets create MONGO_URI \
  --replication-policy="automatic"

gcloud secrets versions add MONGO_URI \
  --data-file=<(printf '%s' "${MONGO_URI_VAL}")
```

Do not commit the connection string. If `MONGO_URI` already exists, add a new version instead of creating the secret again.

## 3. Store AI Provider API Keys

Create a Secret Manager entry for the Google Gemini provider used by `inference`:

```bash
# Google Gemini API Key
gcloud secrets create GEMINI_API_KEY --replication-policy="automatic"
gcloud secrets versions add GEMINI_API_KEY \
  --data-file=<(printf '%s' "GEMINI_API_KEY")
```

---

## 4. Create the Cloud Run Runtime Account & Grant Access

The Cloud Run services run as the dedicated account `exan-cloudrun-runtime@${PROJECT_ID}.iam.gserviceaccount.com`. The GitHub Actions workflow pins this identity with `--service-account` (from the `GCP_RUN_SERVICE_ACCOUNT` repository secret), and Terraform assigns the same identity to its Cloud Run services.

This account needs `Secret Manager Secret Accessor` access to the application secrets used by the services: `JWT_SECRET`, `MONGO_URI`, and `GEMINI_API_KEY`. The default compute account does not need this role because no deployment path uses it.

```bash
export PROJECT_ID="exan-beta"
export RUNTIME_SA="exan-cloudrun-runtime@${PROJECT_ID}.iam.gserviceaccount.com"

# Create the dedicated runtime account once.
gcloud iam service-accounts create exan-cloudrun-runtime \
  --project="${PROJECT_ID}" \
  --display-name="Exan Cloud Run Runtime SA"

# Grant secret-level access to the runtime account.
for SECRET in JWT_SECRET MONGO_URI GEMINI_API_KEY; do
  gcloud secrets add-iam-policy-binding "${SECRET}" \
    --project="${PROJECT_ID}" \
    --member="serviceAccount:${RUNTIME_SA}" \
    --role="roles/secretmanager.secretAccessor"
done
```

If `exan-cloudrun-runtime` already exists, skip the create command. Secret-level grants keep unrelated project secrets inaccessible to the runtime account.

---

## 5. Verify Secrets Configuration

List all registered secrets and confirm versions are active:

```bash
gcloud secrets list

# Test retrieving payload (example for JWT_SECRET)
gcloud secrets versions access latest --secret="JWT_SECRET"

# Confirm the IAM policy is present on application secrets.
gcloud secrets get-iam-policy JWT_SECRET --project="${PROJECT_ID}"
gcloud secrets get-iam-policy MONGO_URI --project="${PROJECT_ID}"
```

---

## 6. Configure GitHub Actions Secrets for GCP Authentication

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
