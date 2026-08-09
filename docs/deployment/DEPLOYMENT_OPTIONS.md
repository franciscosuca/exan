# First Release Deployment Options

This document evaluates hosting options for the **first beta deployment** of Exan and records the recommendation, the trade-offs of each platform, the container topology decision (managed containers vs. Kubernetes), and the infrastructure automation decision.

It expands [Deployment and networking](../scanning/ARCHITECTURE_OPTIONS.md#deployment-and-networking) from the architecture options with concrete platforms and costs.

## Table of Contents

- [Summary](#summary)
- [What We Are Deploying](#what-we-are-deploying)
- [Platform Options](#platform-options)
  - [Option 1: Cloud Run + Firebase Hosting (recommended)](#option-1-cloud-run--firebase-hosting-recommended)
  - [Option 2: Single Compute Engine VM running Docker Compose](#option-2-single-compute-engine-vm-running-docker-compose)
  - [Option 3: GKE Autopilot (Kubernetes)](#option-3-gke-autopilot-kubernetes)
  - [Option 4: Firebase only](#option-4-firebase-only)
  - [Option 5: Non-GCP PaaS (Render, Railway, Fly.io)](#option-5-non-gcp-paas-render-railway-flyio)
- [Comparison Table](#comparison-table)
- [Containers or Kubernetes Pods?](#containers-or-kubernetes-pods)
- [Infrastructure Automation](#infrastructure-automation)
- [Blockers to Resolve Before the Beta](#blockers-to-resolve-before-the-beta)
- [Target Topology](#target-topology)
- [Rollout Checklist](#rollout-checklist)

## Summary

**Recommendation: deploy the beta on Google Cloud Run, serve the React build from Firebase Hosting, and use MongoDB Atlas for the database.**

- **Best fit:** `inference` and `auth-server` are stateless HTTP containers with bursty, low beta traffic. Cloud Run scales them to zero between testers, so idle cost is close to nothing.
- **Cheapest:** the Cloud Run free tier plus Firebase Hosting's free static tier plus an Atlas free-tier cluster keeps a small beta near zero cost. Kubernetes cannot match this because a cluster bills continuously.
- **Easiest:** the existing `Dockerfile.auth` and `inference/Dockerfile` are reused as-is; there is no cluster, node pool, or ingress controller to operate.
- **Separate containers, not pods.** Keep one deployable per service on a managed platform. Kubernetes only becomes worthwhile once we need multi-replica shared state, background workers, and independent scaling — the [Option 3: Independently scaled services](../scanning/ARCHITECTURE_OPTIONS.md#option-3-independently-scaled-services) stage.
- **Automate with Terraform** for the cloud resources and GitHub Actions for build and deploy. Terraform is worth it even at this size because it captures the IAM, secrets, and service wiring that are hard to reproduce by hand.

If the beta must be live in days rather than weeks, [Option 2](#option-2-single-compute-engine-vm-running-docker-compose) (one VM running the current `docker-compose.yml`) is the zero-rewrite fallback and can be replaced by Cloud Run later without changing application code.

## What We Are Deploying

| Service | Image | Port | State | Beta notes |
|---------|-------|------|-------|------------|
| `webapp` | nginx serving the Vite build | 80 | Stateless | Static assets plus a reverse proxy for `/api/*` |
| `inference` | Python 3.11 + FastAPI | 8000 | **In-process workflow state** | Long AI calls, large uploads, needs generous timeouts |
| `auth-server` | Node 20 + Express + tsx | 3001 | Stateless | Needs `JWT_SECRET` and `MONGO_URI` |
| `mongodb` | `mongo:7` | 27017 | **Persistent volume** | Only stores users today |

The two properties that drive the decision are the inference service's *in-memory* workflow state (see [Blockers](#blockers-to-resolve-before-the-beta)) and MongoDB's need for durable storage.

## Platform Options

### Option 1: Cloud Run + Firebase Hosting (recommended)

**Shape:** `inference` and `auth-server` deploy as two Cloud Run services from the existing Dockerfiles. The webapp is built with `bun run build` and published to Firebase Hosting, whose `rewrites` forward `/api/auth/**` to the auth service and `/api/**` to the inference service, replacing `webapp/nginx.conf` in the cloud environment. MongoDB moves to MongoDB Atlas. Secrets live in Secret Manager.

**Pros**

- Scale-to-zero: no traffic from beta testers means no compute bill.
- Generous always-free tier (requests, vCPU-seconds, GiB-seconds) plus Firebase Hosting's free storage and transfer allowance.
- Managed TLS, custom domain, and a global CDN for the SPA, with no nginx to operate.
- Per-service revisions, traffic splitting, and instant rollback.
- Native Secret Manager, Cloud Logging, and Cloud Monitoring integration.
- Long Cloud Run request timeouts (up to 60 minutes) when a service is invoked directly, which comfortably cover slow grading calls.

**Cons**

- **32 MiB request limit** on the standard HTTP/1 path, while `nginx.conf` currently allows `client_max_body_size 50M`. Multi-file student uploads must be split, streamed over HTTP/2, or routed through signed-URL uploads to Cloud Storage.
- **Firebase Hosting rewrites time out after 60 seconds**, far below Cloud Run's own limit. Grading requests that run longer must either bypass the rewrite (map a domain or an external HTTPS load balancer straight to Cloud Run) or become asynchronous jobs the frontend polls.
- Hosting rewrites call Cloud Run over its public endpoint without an identity token, so those services must allow unauthenticated invocations and cannot use internal-only ingress. Application-level JWT checks on `/api/exam/*` are therefore mandatory, not optional.
- Cold starts add a few seconds to the first request after idle.
- The in-memory workflow repository breaks as soon as a second instance starts, so the beta must pin `max-instances` (or move state to MongoDB).
- No local Ollama or LM Studio; only cloud providers work unless a GPU-backed service is added later.
- The container filesystem is ephemeral, so the `./logs` volume mount has no direct equivalent.
- Firebase Hosting rewrites to Cloud Run require the services to sit in a supported region in the same project.

### Option 2: Single Compute Engine VM running Docker Compose

**Shape:** One small VM (for example `e2-small`) with Docker installed, running the current `docker-compose.yml` behind Caddy or nginx for TLS.

**Pros**

- Zero rewrite: the compose file, nginx proxy, volumes, and 50 MB upload limit all work unchanged.
- Local providers (Ollama, LM Studio) stay reachable, and MongoDB keeps a real disk.
- Predictable flat monthly cost and a trivial mental model.

**Cons**

- Always-on billing even with no testers, and no scale-out.
- We own OS patching, TLS renewal, backups, monitoring, and restart-on-failure.
- Single point of failure; deploys mean SSH plus `docker compose up -d`.
- Published container ports currently bypass nginx as a security boundary and must be closed before the VM is exposed.

### Option 3: GKE Autopilot (Kubernetes)

**Shape:** All four services as Deployments in one Autopilot cluster, MongoDB as a StatefulSet or on Atlas, traffic through a GKE Ingress or Gateway.

**Pros**

- Real orchestration: self-healing, rolling updates, horizontal pod autoscaling, network policies, and disruption budgets.
- Runs stateful workloads natively through StatefulSets and persistent volumes.
- Portable manifests across clouds; the obvious destination once services must scale independently.

**Cons**

- The most expensive option: a cluster management fee plus continuously billed pod resources and a load balancer, none of which scale to zero.
- Highest operational surface: manifests or Helm charts, ingress, certificate management, secrets, and cluster upgrades.
- Solves scaling problems Exan does not have yet — beta traffic is a handful of testers.
- Self-hosting MongoDB on Kubernetes adds backup and failover work that Atlas provides out of the box.

### Option 4: Firebase only

**Shape:** Firebase Hosting for the SPA plus Cloud Functions or Firebase App Hosting for backends, with Firestore replacing MongoDB.

**Pros**

- Simplest single-vendor developer experience, and Firebase Auth could replace the whole `auth/` service.
- Excellent static hosting, preview channels, and CDN.

**Cons**

- App Hosting targets SSR frameworks (Next.js, Angular); a containerized FastAPI service is not its intended workload, so backends land on Cloud Run anyway.
- Cloud Functions are a poor fit for PyMuPDF/Pillow-heavy processing and long AI calls.
- Replacing MongoDB with Firestore and Express JWT with Firebase Auth is a rewrite of `auth/` and `db/` for no beta benefit.

**Verdict:** use Firebase for *hosting the frontend only*, which is exactly what Option 1 does.

### Option 5: Non-GCP PaaS (Render, Railway, Fly.io)

**Shape:** Push the same Dockerfiles to a container PaaS; most offer managed static sites plus a Mongo add-on or an Atlas link.

**Pros**

- Fastest path from a Dockerfile to a URL, often straight from a GitHub repo.
- Cheap hobby tiers; Fly.io also offers scale-to-zero and multi-region.
- No GCP IAM learning curve.

**Cons**

- Leaves the GCP ecosystem the issue targets, splitting secrets, logging, and billing across vendors.
- Weaker compliance story for an education product handling student work.
- Free tiers idle aggressively and are less predictable than Cloud Run's documented limits.

## Comparison Table

| Criterion | Cloud Run + Firebase | Compute Engine VM | GKE Autopilot | Firebase only | PaaS |
|-----------|----------------------|-------------------|---------------|---------------|------|
| Idle cost | ~zero (scales to zero) | Always-on VM | Highest (cluster + pods) | ~zero | Low |
| Setup effort | Low | Lowest | High | Medium | Lowest |
| Ops burden | Low | High (we own the OS) | High | Low | Low |
| Reuses current Dockerfiles | Yes (webapp becomes static) | Yes, unchanged | Yes | No | Yes |
| Uploads above 32 MiB | Needs work | Works today | Works | Needs work | Varies |
| Persistent MongoDB | Atlas | Local volume | StatefulSet or Atlas | Firestore rewrite | Add-on or Atlas |
| Path to scale | Good | Poor | Best | Limited | Good |
| **Beta verdict** | **Recommended** | Fast fallback | Premature | Frontend only | Viable alternative |

## Containers or Kubernetes Pods?

**Separate managed containers on a shared private network — not pods — for the first release.**

- Exan has four services and no background workers, queues, or cross-service leader election. Kubernetes' scheduling, service mesh, and autoscaling primitives would sit unused while billing continuously.
- Cloud Run gives each service its own URL, revision history, IAM identity, and autoscaling policy. Because Firebase Hosting rewrites invoke the services anonymously over their public endpoints, the services stay publicly reachable and the security boundary is the JWT check inside each service rather than network ingress. An external HTTPS load balancer with Cloud Armor or IAP is the upgrade path if network-level restriction becomes a requirement.
- The `webapp` nginx container stops being a runtime service in the cloud and becomes a build artifact on a CDN, removing one container from the deployment while local Compose development stays unchanged.
- Kubernetes becomes the right answer at the [Independently scaled services](../scanning/ARCHITECTURE_OPTIONS.md#option-3-independently-scaled-services) stage: shared workflow state, async grading workers, and per-workload scaling. The same images and twelve-factor configuration port to Kubernetes without application changes, so this decision is not a dead end.

`docker-compose.yml` remains the supported local development and self-hosting path either way.

## Infrastructure Automation

**Use Terraform for cloud resources and GitHub Actions for build and deploy.**

| Approach | Pros | Cons | Verdict |
|----------|------|------|---------|
| **Terraform** | Cloud-agnostic, reviewable state, one place for services, IAM, secrets, registry, and DNS; recreates the environment for staging | Extra language, remote state bucket, and drift management | **Recommended** |
| `gcloud` shell scripts | No new tooling, easy to start | No state or drift detection; degenerates into untracked click-ops | Bootstrap only |
| Cloud Deployment Manager | Native to GCP | Effectively legacy; Google steers users to Terraform via Infrastructure Manager | Avoid |
| Pulumi | Real TypeScript, familiar to this repo | Smaller ecosystem; another runtime in CI | Reasonable alternative |
| Helm / Kustomize | Standard for Kubernetes | Only relevant if we adopt GKE | Deferred |

Suggested split:

- **Terraform** owns Artifact Registry, the two Cloud Run services, service accounts and IAM bindings, Secret Manager entries, the Firebase Hosting site, and the custom domain. Keep state in a GCS bucket.
- **GitHub Actions** owns CI (the existing Vitest and pytest suites), image build and push, `gcloud run deploy` of the new image, and `firebase deploy --only hosting`. Authenticate with Workload Identity Federation so no long-lived service-account key is stored in the repo.
- Secret *values* (`JWT_SECRET`, provider API keys, `MONGO_URI`) are created outside Terraform and only referenced by it, so no secret ever lands in state or in git.

## Blockers to Resolve Before the Beta

1. **In-memory workflow state.** `inference` keeps exam and answer-key state in process memory, so a second instance loses the workflow. Either pin the service to a single instance for the beta or move the repository to MongoDB — see [Storage and workflow state](../scanning/ARCHITECTURE_OPTIONS.md#storage-and-workflow-state).
2. **Upload size.** `nginx.conf` allows 50 MB while Cloud Run's default HTTP/1 request limit is 32 MiB. Cap client-side upload size, upload files one at a time, or move to direct-to-storage uploads.
3. **Unauthenticated inference endpoints.** `/api/exam/*` has no auth today. Because Hosting rewrites reach Cloud Run anonymously over its public URL, requiring the auth service's JWT inside `inference` is a hard prerequisite for going public.
4. **Published ports.** `docker-compose.yml` publishes 8000, 3001, and 27017. In the deployed environment the database must never be publicly reachable, and every publicly reachable service must authenticate its own requests.
5. **Long grading requests.** Firebase Hosting rewrites cut responses off at 60 seconds. Measure the slowest grading call and, if needed, move grading to an asynchronous job with polling or route it around the rewrite.
6. **Secrets.** `JWT_SECRET` defaults to `change-this-to-a-random-secret` and MongoDB uses `admin`/`admin`. Both must be generated per environment and stored in Secret Manager.
7. **Logs.** Run logging writes to the mounted `./logs` volume, which does not survive an ephemeral container. Write to stdout for Cloud Logging or to a storage bucket.
8. **Local providers.** Ollama and LM Studio are unreachable from managed hosting, so the beta build should hide or disable them.

## Target Topology

```
                    ┌────────────────────────────┐
  Beta tester ────▶ │ Firebase Hosting (CDN+TLS) │  static React build
                    └─────────────┬──────────────┘
                       rewrites   │
              /api/auth/**        │        /api/**
            ┌───────────────────┐ │ ┌────────────────────────┐
            │ Cloud Run         │◀┴▶│ Cloud Run              │
            │ auth-server       │   │ inference (FastAPI)    │
            │ (Node/Express)    │   │ max-instances pinned   │
            └─────────┬─────────┘   └───────────┬────────────┘
                      │                         │
                      ▼                         ▼
            ┌───────────────────┐   ┌────────────────────────┐
            │ MongoDB Atlas     │   │ Secret Manager         │
            │ (users)           │   │ (JWT + provider keys)  │
            └───────────────────┘   └────────────────────────┘
```

## Rollout Checklist

- [ ] Create the GCP project, enable Cloud Run, Artifact Registry, and Secret Manager, and create the Terraform state bucket.
- [ ] Create a MongoDB Atlas cluster and store its connection string in Secret Manager.
- [ ] Generate a strong `JWT_SECRET` and store the provider API keys in Secret Manager.
- [ ] Address the [blockers](#blockers-to-resolve-before-the-beta) — at minimum single-instance pinning, upload limits, and inference authentication.
- [ ] Write the Terraform configuration for registry, services, IAM, secrets, and hosting.
- [ ] Add a GitHub Actions workflow that tests, builds and pushes images, deploys Cloud Run, and deploys Firebase Hosting.
- [ ] Point the Firebase Hosting rewrites at the two Cloud Run services and verify the frontend never calls them directly.
- [ ] Smoke-test the full workflow (template, answer key, grading) against the deployed URL, then invite beta testers.

> Pricing and platform limits change. Confirm the current free-tier allowances and request limits on Google Cloud's pricing and quotas pages before committing.
