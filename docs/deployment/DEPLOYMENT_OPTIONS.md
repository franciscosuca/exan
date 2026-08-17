# First Release Deployment Options

This document evaluates hosting options for the **first beta deployment** of Exan and records the recommendation, the trade-offs of each platform, the container topology decision (managed containers vs. Kubernetes), and the infrastructure automation decision.

It expands [Deployment and networking](../scanning/ARCHITECTURE_OPTIONS.md#deployment-and-networking) from the architecture options with concrete platforms and costs.

## Table of Contents

- [Summary](#summary)
- [What We Are Deploying](#what-we-are-deploying)
- [Platform Options](#platform-options)
  - [Option 1: Cloud Run + Firebase Hosting](#option-1-cloud-run--firebase-hosting)
  - [Option 2: Single Compute Engine VM running Docker Compose](#option-2-single-compute-engine-vm-running-docker-compose)
  - [Option 3: GKE Autopilot (Kubernetes)](#option-3-gke-autopilot-kubernetes)
  - [Option 4: Firebase only](#option-4-firebase-only)
  - [Option 5: Non-GCP PaaS (Render, Railway, Fly.io)](#option-5-non-gcp-paas-render-railway-flyio)
- [Comparison Table](#comparison-table)
- [Cost Estimate](#cost-estimate)
- [Variant: Everything on Cloud Run, Database on Atlas (recommended)](#variant-everything-on-cloud-run-database-on-atlas-recommended)
- [Containers or Kubernetes Pods?](#containers-or-kubernetes-pods)
- [Infrastructure Automation](#infrastructure-automation)
- [Blockers to Resolve Before the Beta](#blockers-to-resolve-before-the-beta)
- [Target Topology](#target-topology)
- [Rollout Checklist](#rollout-checklist)

## Summary

**Recommendation: deploy the beta with all three application services on Google Cloud Run, MongoDB Atlas for persistence, and Secret Manager for credentials.**

- **Best fit:** `webapp`, `inference`, and `auth-server` remain separate HTTP services with bursty, low beta traffic. Cloud Run scales them to zero between testers, while inference stays pinned to one instance until workflow state moves out of memory.
- **Cheapest:** Cloud Run's free tier plus an Atlas free-tier cluster keeps a small beta near zero cost. Kubernetes cannot match this because a cluster bills continuously.
- **Easiest:** the existing Dockerfiles can be reused; only the webapp's nginx upstreams need cloud-specific service URLs. There is no cluster, node pool, or ingress controller to operate.
- **Separate containers, not pods.** Keep one deployable per service on a managed platform. Kubernetes only becomes worthwhile once we need multi-replica shared state, background workers, and independent scaling — the [Option 3: Independently scaled services](../scanning/ARCHITECTURE_OPTIONS.md#option-3-independently-scaled-services) stage.
- **Automate with Terraform** for the cloud resources and GitHub Actions for build and deploy. Terraform is worth it even at this size because it captures the IAM, secrets, and service wiring that are hard to reproduce by hand.

If the beta must be live in days rather than weeks, [Option 2](#option-2-single-compute-engine-vm-running-docker-compose) (one VM running the current `docker-compose.yml`) is the zero-rewrite fallback and can be replaced by Cloud Run later without changing application code.

This choice trades global static asset caching for one deployment surface, private backend routing, and Cloud Run's full request timeout.

## What We Are Deploying

| Service | Image | Port | State | Beta notes |
|---------|-------|------|-------|------------|
| `webapp` | nginx serving the Vite build | 80 | Stateless | Static assets plus a reverse proxy for `/api/*` |
| `inference` | Python 3.11 + FastAPI | 8000 | **In-process workflow state** | Long AI calls, large uploads, needs generous timeouts |
| `auth-server` | Node 20 + Express + tsx | 3001 | Stateless | Needs `JWT_SECRET` and `MONGO_URI` |
| `mongodb` | `mongo:7` | 27017 | **Persistent volume** | Only stores users today |

The two properties that drive the decision are the inference service's *in-memory* workflow state (see [Blockers](#blockers-to-resolve-before-the-beta)) and MongoDB's need for durable storage.

## Platform Options

### Option 1: Cloud Run + Firebase Hosting

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

- The most expensive option: a cluster management fee plus continuously billed pod resources and a load balancer, none of which scale to zero — roughly **$85/month** for the current four services before any traffic, as broken down in [Cost Estimate](#cost-estimate).
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

## Cost Estimate

Approximate `us-central1` list prices for a **beta-sized** deployment of the four services in [What We Are Deploying](#what-we-are-deploying). These are planning figures, not quotes — Google restructured Autopilot pricing in late 2025, so confirm every rate in the [Google Cloud pricing calculator](https://cloud.google.com/products/calculator) before committing.

### GKE, with the current architecture

Sizing all four services as pods with modest resource requests — `webapp` 0.25 vCPU / 0.5 GiB, `auth-server` 0.25 vCPU / 0.5 GiB, `inference` 0.5 vCPU / 1 GiB, `mongodb` 0.5 vCPU / 2 GiB — gives **1.5 vCPU and 4 GiB** of requests running 24/7 (~730 h/month).

| Line item | Basis | Monthly |
|-----------|-------|---------|
| Cluster management fee | $0.10/cluster/hour, charged on every cluster in any mode | $73 |
| GKE free-tier credit | $74.40/month per billing account, covers **one** Autopilot or zonal Standard cluster | −$73 |
| Autopilot pod vCPU | 1.5 vCPU × ~$0.0445/vCPU-hour | ~$49 |
| Autopilot pod memory | 4 GiB × ~$0.0049/GiB-hour | ~$14 |
| External HTTP(S) load balancer | $0.025/hour per forwarding rule + data processing | ~$18 |
| Persistent disk for MongoDB | 20 GiB balanced at ~$0.10/GiB-month | ~$2 |
| **Total (Autopilot, one cluster)** | | **~$85/month** |

Realistic variations:

- **Second environment.** A staging cluster loses the free-tier credit, so the second cluster adds its own $73 fee: **~$160/month** for the pair.
- **GKE Standard** instead of Autopilot: two `e2-standard-2` nodes at ~$49 each = ~$98, plus the load balancer, boot disks, and the same cluster fee treatment → **~$120/month**, and now we also own node upgrades and bin-packing.
- **MongoDB Atlas instead of an in-cluster StatefulSet** removes the disk line but adds $0 (M0 free tier) to ~$57/month (M10) — while removing the backup, failover, and upgrade work.
- **Growth.** Costs scale roughly linearly with pod requests: doubling `inference` to 1 vCPU / 2 GiB adds ~$20/month.

The important property is the **floor**: even with zero beta traffic, GKE bills roughly $85/month because pods and the load balancer run continuously. Nothing in the current architecture scales to zero.

### The recommended stack, for comparison

| Line item | Basis | Monthly |
|-----------|-------|---------|
| Cloud Run (`inference` + `auth-server`) | Scale to zero; the free tier covers ~2M requests, 180k vCPU-seconds, and 360k GiB-seconds | $0 for a small beta |
| Firebase Hosting | Free tier covers 10 GB storage and 360 MB/day transfer | $0 |
| MongoDB Atlas M0 | Free forever, 512 MB, auto-pauses when idle | $0 |
| Artifact Registry | A few GB of images at ~$0.10/GB-month | <$1 |
| **Total** | | **~$0–5/month** |

A beta that runs, say, 200 grading requests per month at 30 seconds and 1 vCPU / 2 GiB each consumes ~6,000 vCPU-seconds and ~12,000 GiB-seconds — a few percent of the Cloud Run free tier. Cost only becomes meaningful once real traffic arrives, and then it grows with usage rather than with wall-clock time.

Note that this stack is **not three vendors to wire together**: Cloud Run, Firebase Hosting, Artifact Registry, and Secret Manager all live in the *same* GCP project and one bill, and Hosting reaches Cloud Run through a `rewrites` entry in `firebase.json` rather than through networking we configure. MongoDB Atlas is the only third party, and it can be replaced with Firestore or a self-managed MongoDB if a single-vendor bill matters more than staying on the current driver.

### Where the money goes

Against roughly $85/month for GKE, the AI provider calls themselves will likely dominate the bill for a beta of this size. Paying a fixed cluster fee to orchestrate four containers that see intermittent traffic buys availability and scaling guarantees the beta does not need yet — which is the cost argument behind [Containers or Kubernetes Pods?](#containers-or-kubernetes-pods).

### Variant: Everything on Cloud Run, Database on Atlas (recommended)

The selected deployment is to deploy **all three application containers — `webapp`, `auth-server`, `inference` — as Cloud Run services**, keeping only MongoDB on Atlas. The existing `webapp/Dockerfile` and `nginx.conf` provide the starting point; nginx serves the built SPA and reverse-proxies `/api/auth/` and `/api/` to the two backend services, with cloud-specific upstream URLs replacing the Compose service names.

### Advantages

- **One platform, one deploy verb.** Three `gcloud run deploy` calls, one Terraform resource type, one set of IAM rules, one log view. There is no `firebase.json`, no Firebase CLI in CI, and no second deployment target that can drift from the images.
- **The Compose topology is preserved.** `nginx.conf` stays the single routing definition for both local development and production, so a route added locally behaves the same way deployed. Under the Firebase variant the routing rules exist twice — in `nginx.conf` for Compose and in `firebase.json` rewrites for the cloud — and can silently disagree.
- **No 60-second rewrite ceiling.** This is the significant one. Firebase Hosting cuts a rewritten response at 60 seconds; a Cloud Run frontend proxying to Cloud Run backends is bound only by Cloud Run's own request timeout, configurable up to 60 minutes. Slow grading calls stop being a blocker and [Blocker 5](#blockers-to-resolve-before-the-beta) mostly disappears.
- **Backends can stop being public.** Because the caller is now a service we control rather than Firebase's edge, `auth-server` and `inference` can be set to internal-only ingress reached over Direct VPC egress, so only `webapp` has a public URL. Under the Hosting variant the backends must accept anonymous public traffic.
- **Same-origin by construction.** Everything is served from one hostname, so there is no CORS configuration and no third deployment surface for cookies or CSP to account for.
- **Still scales to zero**, and the free tier still covers a beta.

### Disadvantages

- **The SPA loses the CDN.** Firebase Hosting serves static assets from a global edge cache; a Cloud Run container serves them from one region, on a billed request, after a possible cold start. First paint from a distant tester is measurably slower, and *every* asset request wakes or occupies an instance instead of being answered at the edge.
- **Cold starts now hit the first page load,** not just the first API call — the worst place to put them for a beta tester's first impression. Avoiding that means `min-instances = 1` on `webapp`, which gives up scale-to-zero for the one service that would otherwise be nearly free, or fronting it with Cloud CDN and an external HTTPS load balancer at roughly $18/month, which erases the cost advantage.
- **An extra hop and an extra hop's worth of billing.** Each `/api/*` call occupies a `webapp` instance for the whole duration of the backend call, so slow grading requests are billed twice — once on `inference`, once on the nginx container holding the connection open.
- **`nginx.conf` needs cloud-specific edits after all.** `proxy_pass http://auth-server:3001/` relies on Compose DNS. In Cloud Run the upstreams are HTTPS URLs that only exist after the services are created, which means an nginx `resolver`, `proxy_ssl_server_name on`, and `proxy_set_header Host` matching the target — plus templating the URLs in at deploy time. The "unchanged config" advantage is real but partial.
- **Internal ingress is not free of work.** It requires Direct VPC egress (or a connector) on `webapp`, and if the backends are set to require IAM authentication, nginx cannot mint the ID token — that would force a small proxy in application code instead. Practically, the beta keeps ingress internal and authenticates with JWTs, as [Blocker 3](#blockers-to-resolve-before-the-beta) requires anyway.
- **The 32 MiB request limit does not go away.** It applies to the `webapp` service too, so `client_max_body_size 50M` remains misleading and uploads still need capping or a direct-to-storage path.
- **No preview channels, no atomic static rollback.** Firebase Hosting gives per-PR preview URLs and instant rollback of a static release for free; here a frontend change is a container build and a revision rollout.

### Verdict

**Use this variant for the beta.** It keeps the deployment and routing surface in one platform, avoids a hosting rewrite timeout, and preserves MongoDB Atlas as the managed persistence layer. A CDN-backed static frontend can be introduced later without changing the backend services.



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

- **Terraform** owns Artifact Registry, the three Cloud Run services, service accounts and IAM bindings, Secret Manager entries, and the custom domain. Keep state in a GCS bucket.
- **GitHub Actions** owns CI (the existing Vitest and pytest suites), image build and push, and `gcloud run deploy` for `webapp`, `auth-server`, and `inference`. Authenticate with Workload Identity Federation so no long-lived service-account key is stored in the repo.
- Secret *values* (`JWT_SECRET`, provider API keys, `MONGO_URI`) are created outside Terraform and only referenced by it, so no secret ever lands in state or in git.

## Blockers to Resolve Before the Beta

1. **In-memory workflow state.** `inference` keeps exam and answer-key state in process memory, so a second instance loses the workflow. Either pin the service to a single instance for the beta or move the repository to MongoDB — see [Storage and workflow state](../scanning/ARCHITECTURE_OPTIONS.md#storage-and-workflow-state).
2. **Upload size.** `nginx.conf` allows 50 MB while Cloud Run's default HTTP/1 request limit is 32 MiB. Cap client-side upload size, upload files one at a time, or move to direct-to-storage uploads.
3. **Unauthenticated inference endpoints.** `/api/exam/*` has no auth today. Because Hosting rewrites reach Cloud Run anonymously over its public URL, requiring the auth service's JWT inside `inference` is a hard prerequisite for going public.
4. **Published ports.** `docker-compose.yml` publishes 8000, 3001, and 27017. In the deployed environment the database must never be publicly reachable, and every publicly reachable service must authenticate its own requests.
5. **Long grading requests.** Set the Cloud Run timeouts for `webapp` and `inference` high enough for the slowest grading call. If calls approach the platform limit, move grading to an asynchronous job with polling.
6. **Secrets.** `JWT_SECRET` defaults to `change-this-to-a-random-secret` and MongoDB uses `admin`/`admin`. Both must be generated per environment and stored in Secret Manager.
7. **Logs.** Run logging writes to the mounted `./logs` volume, which does not survive an ephemeral container. Write to stdout for Cloud Logging or to a storage bucket.
8. **Local providers.** Ollama and LM Studio are unreachable from managed hosting, so the beta build should hide or disable them.

## Target Topology

**Beta verdict:** use the all-on-Cloud-Run variant: deploy `webapp`, `auth-server`, and `inference` as separate Cloud Run services, keep MongoDB on Atlas, and store credentials in Secret Manager. Pin `inference` to one instance until workflow state is externalized.

```
                    ┌────────────────────────────┐
  Beta tester ────▶ │ Cloud Run: webapp           │  React build + nginx
                    └─────────────┬──────────────┘
              /api/auth/**        │        /api/**
            ┌─────────▼─────────┐   ┌──────────▼─────────────┐
            │ Cloud Run         │   │ Cloud Run               │
            │ auth-server       │   │ inference (FastAPI)     │
            │ (Node/Express)    │   │ max-instances pinned    │
            └─────────┬─────────┘   └──────────┬──────────────┘
                      │                         │
                      ▼                         ▼
            ┌───────────────────┐   ┌────────────────────────┐
            │ MongoDB Atlas     │   │ Secret Manager         │
            │ (users)           │   │ (JWT, Mongo URI, keys)  │
            └───────────────────┘   └────────────────────────┘
```

## Rollout Checklist

- [ ] Create the GCP project, enable Cloud Run, Artifact Registry, and Secret Manager, and create the Terraform state bucket.
- [ ] Create a MongoDB Atlas cluster and store its connection string in Secret Manager.
- [ ] Generate a strong `JWT_SECRET` and store the provider API keys in Secret Manager.
- [ ] Address the [blockers](#blockers-to-resolve-before-the-beta) — at minimum single-instance pinning, upload limits, and inference authentication.
- [ ] Write the Terraform configuration for the registry, three Cloud Run services, IAM, secrets, and custom-domain routing.
- [ ] Add a GitHub Actions workflow that tests, builds and pushes all images, then deploys `webapp`, `auth-server`, and `inference` to Cloud Run.
- [ ] Configure the Cloud Run webapp to proxy `/api/auth/**` and `/api/**` to the backend services, and verify the frontend never calls backend URLs directly.
- [ ] Smoke-test the full workflow (template, answer key, grading) against the deployed URL, then invite beta testers.

> Pricing and platform limits change. Confirm the current free-tier allowances and request limits on Google Cloud's pricing and quotas pages before committing.
