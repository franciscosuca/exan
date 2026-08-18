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
echo -n "${JWT_SECRET_VAL}" | \
  gcloud secrets versions add JWT_SECRET --data-file=-
```

---

## 2. Store AI Provider API Keys

Create Secret Manager entries for each external LLM / AI vision provider used by `inference`:

```bash
# OpenAI API Key
gcloud secrets create OPENAI_API_KEY --replication-policy="automatic"
echo -n "sk-your-openai-api-key" | gcloud secrets versions add OPENAI_API_KEY --data-file=-

# Anthropic API Key
gcloud secrets create ANTHROPIC_API_KEY --replication-policy="automatic"
echo -n "sk-ant-your-anthropic-key" | gcloud secrets versions add ANTHROPIC_API_KEY --data-file=-

# Google Gemini API Key
gcloud secrets create GEMINI_API_KEY --replication-policy="automatic"
echo -n "AIzaSy-your-gemini-key" | gcloud secrets versions add GEMINI_API_KEY --data-file=-
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

## Official Documentation & References

- [GCP Secret Manager Quickstart](https://cloud.google.com/secret-manager/docs/quickstart)
- [Secret Manager IAM Access Control](https://cloud.google.com/secret-manager/docs/access-control)
- [Mounting Secrets in Cloud Run](https://cloud.google.com/run/docs/configuring/secrets)
- [OpenAI API Keys](https://platform.openai.com/api-keys)
- [Anthropic API Keys](https://console.anthropic.com/settings/keys)
- [Google AI Studio (Gemini) API Keys](https://aistudio.google.com/app/apikey)
