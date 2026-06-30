# GCP Cloud Build Deployment Guide

This guide explains how to set up automated deployment to Google
Cloud Run based on semantic-release tags.

## Architecture

```bash
Git Commit → GitHub Actions (semantic-release) → Create Tag
                                                    ↓
                                          Cloud Build Trigger
                                                    ↓
                                    Build Docker Image & Push
                                                    ↓
                                      Deploy to Cloud Run
```

## Setup Instructions

### 1. Connect GitHub Repository to Cloud Build

```bash
gcloud builds connect --name=countdown --repo-name=countdown \
--repo-owner=franciscosuca --region=europe-west1
```

### 2. Create Cloud Build Trigger for Tags

Use the GCP Console or CLI:

**Via gcloud CLI:**

```bash
gcloud builds triggers create github \
  --name=countdown-deploy-on-tag \
  --repo-name=countdown \
  --repo-owner=franciscosuca \
  --tag-pattern="^v.*$" \
  --filename=cloudbuild.yaml \
  --region=europe-west1
```

**Via GCP Console:**

1. Go to [Cloud Build Triggers](https://console.cloud.google.com/cloud-build/triggers)
2. Click "Create Trigger"
3. Configure:
   - **Name:** countdown-deploy-on-tag
   - **Source:** GitHub (franciscosuca/countdown)
   - **Event:** Push to a tag
   - **Tag (regex):** `^v.*$` (matches v1.0.0, v2.1.0, etc.)
   - **Build configuration:** Cloud Build configuration file
   - **Location:** cloudbuild.yaml

### 3. Update Substitutions (Optional)

In the trigger settings, you can override default substitutions:

- `_SERVICE_NAME` - Cloud Run service name (default: countdown)
- `_REGION` - GCP region (default: europe-west1)

### 4. Set Required IAM Permissions

Ensure the Cloud Build service account has permissions to:

- Deploy to Cloud Run
- Push to Container Registry
- Write logs to Cloud Logging

```bash
PROJECT_ID=$(gcloud config get-value project)
CLOUD_BUILD_SA="${PROJECT_ID}@cloudbuild.gserviceaccount.com"

# Grant Cloud Run Admin role
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$CLOUD_BUILD_SA \
  --role=roles/run.admin

# Grant Service Account User role
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$CLOUD_BUILD_SA \
  --role=roles/iam.serviceAccountUser

# Grant logging permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$CLOUD_BUILD_SA \
  --role=roles/logging.logWriter
```

## Deployment Workflow

### When a commit is pushed to main

1. **GitHub Actions** (`.github/workflows/build-and-release.yml`):
   - Runs tests
   - Builds the app
   - Runs semantic-release
   - Creates a new tag (e.g., v1.4.2) if changes warrant a version bump

2. **Cloud Build** (triggered automatically on tag):
   - Builds Docker image: `gcr.io/PROJECT_ID/countdown:SHORT_SHA`
   - Pushes to Container Registry
   - Deploys to Cloud Run with:
     - Port: 8080
     - Memory: 512Mi
     - CPU: 1
     - Allow unauthenticated requests

3. **Cloud Logging**:
   - All build logs are stored in Cloud Logging (not in a Cloud Storage bucket)
   - Logs are queryable via Cloud Logging console or CLI

## Monitoring Deployments

### View build history

```bash
gcloud builds list --filter="substitutions._SERVICE_NAME=countdown"
```

### View specific build logs

```bash
gcloud builds log BUILD_ID
```

### View Cloud Run deployments

```bash
gcloud run services describe countdown --region=europe-west1
```

### View recent Cloud Run revisions

```bash
gcloud run revisions list --service=countdown --region=europe-west1
```

## Troubleshooting

### Build fails with "invalid argument" for logging options

This was the original issue. Make sure `cloudbuild.yaml` includes:

```yaml
options:
  logging: CLOUD_LOGGING_ONLY
```

This fixes the conflict when using a service account without specifying a logs bucket.

### Trigger not firing on tags

1. Verify the tag pattern in the trigger matches semantic-release output (should be `v*` format)
2. Check GitHub repository is connected: `gcloud builds connect --list`
3. Ensure the branch condition (if any) doesn't block tag triggers

### Cloud Run deployment fails

1. Check IAM permissions for Cloud Build service account
2. Verify the image was successfully pushed to Container Registry
3. Check if Cloud Run service already exists; may need `--allow-unauthenticated` flag

## Rollback Procedure

To rollback to a previous deployment:

```bash
# List available revisions
gcloud run revisions list --service=countdown --region=europe-west1

# Deploy a specific revision
gcloud run services update-traffic countdown --to-revisions=REVISION_NAME=100 --region=europe-west1
```

Or trigger a new build with the previous tag:

```bash
git tag v1.4.0  # Create/recreate an old tag
git push origin v1.4.0
```
