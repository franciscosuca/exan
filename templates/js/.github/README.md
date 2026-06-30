# GitHub Actions Workflow

This template includes automated build and release workflows via GitHub Actions.

## Workflow Overview

The CI/CD pipeline is triggered on:

- Push to `main` - Runs build, tests, and releases
- Push to `pre-release` - Runs build, tests, and releases (beta version)
- Pull requests to `main` - Runs build and tests only
- Manual trigger via `workflow_dispatch` - Can select environment

## Build Process

The workflow automatically:

1. Checks out code with full git history
2. Sets up Node.js 20 with npm caching
3. Installs dependencies with `npm ci`
4. Runs tests with `npm test`
5. Builds the application with `npm run build`
6. Runs semantic-release for automatic versioning

## Required Secrets

For semantic-release to work properly, configure these GitHub Secrets:

- `GITHUB_TOKEN` - Automatically provided by GitHub Actions
- `NPM_TOKEN` (optional) - For npm package publishing

## Deploying to GCP

After the workflow builds and releases your project, you can deploy to Google Cloud Platform using the GCP Console:

### Option 1: Deploy Docker Image from Container Registry

1. **Push Docker image to GCP Container Registry**

   ```bash
   docker build -t gcr.io/PROJECT_ID/IMAGE_NAME:TAG .
   docker push gcr.io/PROJECT_ID/IMAGE_NAME:TAG
   ```

2. **Deploy to Cloud Run via GCP Console**
   - Go to [Cloud Run](https://console.cloud.google.com/run)
   - Click "Create Service"
   - Select your container image from Container Registry
   - Configure:
     - Service name
     - Region
     - CPU allocation and memory
     - Environment variables
   - Click "Create"

### Option 2: Deploy to Cloud Run from Source

1. In GCP Console, go to Cloud Run
2. Click "Create Service"
3. Select "Deploy one-off revision from source code"
4. Connect to your GitHub repository
5. Select this branch/repository
6. Configure build settings:
   - Runtime: Node.js 20
   - Build type: Dockerfile
7. Configure deployment settings
8. Click "Create"

### Option 3: Deploy to App Engine

1. Ensure you have an `app.yaml` file in your project root
2. Go to [App Engine](https://console.cloud.google.com/appengine)
3. Click "Deploy" and follow the wizard
4. Or use the `gcloud` CLI:

   ```bash
   gcloud app deploy
   ```

### Option 4: Deploy to Cloud Functions

1. Go to [Cloud Functions](https://console.cloud.google.com/functions)
2. Click "Create Function"
3. Configure:
   - Runtime: Node.js 20
   - Entry point: your function name
   - Source code: inline, zipped source, or GitHub
4. Click "Create"

## Environment Variables

When deploying to GCP, set any required environment variables in:

- Cloud Run: Service settings → Environment variables
- App Engine: app.yaml configuration
- Cloud Functions: Function settings

## Monitoring Deployments

Monitor your deployments via:

- [Cloud Run Dashboard](https://console.cloud.google.com/run)
- [Cloud Logging](https://console.cloud.google.com/logs)
- [Cloud Trace](https://console.cloud.google.com/traces) for performance insights

## Additional Resources

- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Google Cloud SDK CLI](https://cloud.google.com/sdk/docs)
- [Semantic Release Documentation](https://semantic-release.gitbook.io/)
