# Architecture Options

This document contains the architecture choices referenced by [ARCHITECTURE.md](../ARCHITECTURE.md). Each option is grouped by the decision it informs, with subtopics for trade-offs, project fit, and migration impact.

## Table of Contents

- [Service topology](#service-topology)
  - [Option 1: Current modular services](#option-1-current-modular-services)
  - [Option 2: Consolidated application](#option-2-consolidated-application)
  - [Option 3: Independently scaled services](#option-3-independently-scaled-services)
- [Runtime provider credentials](#runtime-provider-credentials)
  - [Option 1: Deployment-managed credentials](#option-1-deployment-managed-credentials)
  - [Option 2: Short-lived server connections](#option-2-short-lived-server-connections)
  - [Option 3: Persistent encrypted credentials](#option-3-persistent-encrypted-credentials)
- [Phone scanning and desktop handoff](#phone-scanning-and-desktop-handoff)
  - [Option 1: Mobile browser capture](#option-1-mobile-browser-capture)
  - [Option 2: QR-paired web uploader](#option-2-qr-paired-web-uploader)
  - [Option 3: Native companion application](#option-3-native-companion-application)
- [Storage and workflow state](#storage-and-workflow-state)
  - [Option 1: Process memory](#option-1-process-memory)
  - [Option 2: Shared TTL storage](#option-2-shared-ttl-storage)
  - [Option 3: Durable workflow storage](#option-3-durable-workflow-storage)
- [Deployment and networking](#deployment-and-networking)
  - [Option 1: Docker Compose](#option-1-docker-compose)
  - [Option 2: Managed container deployment](#option-2-managed-container-deployment)

## Service Topology

### Option 1: Current modular services

**Shape:** React webapp, FastAPI inference, Express auth, MongoDB, and nginx.

**Advantages:** Clear ownership, Python-native AI integrations, independent frontend and inference tooling, and a small local deployment story.

**Trade-offs:** Cross-service authentication and API contracts need explicit maintenance. Local in-memory inference state limits horizontal scaling.

**Project fit:** Recommended for the current product stage. Keep service boundaries stable while hardening authentication and ownership checks.

### Option 2: Consolidated application

**Shape:** Combine authentication and inference behind one application boundary, with the webapp remaining separate.

**Advantages:** Fewer network hops, simpler local development, and one server-side request boundary.

**Trade-offs:** Couples Node authentication to Python inference concerns or requires a larger rewrite. It also reduces independent scaling and deployment flexibility.

**Project fit:** Useful only if operational simplicity becomes more important than the existing language-specific provider integrations.

### Option 3: Independently scaled services

**Shape:** Keep the current services and add shared persistence, background jobs, and separate scaling for uploads, inference, and results.

**Advantages:** Better isolation for expensive workloads, resilient multi-instance operation, and clearer resource controls.

**Trade-offs:** Requires shared state, queueing, observability, deployment automation, and stronger API versioning.

**Project fit:** A later evolution after authenticated ownership and durable workflow requirements are established.

## Runtime Provider Credentials

The full provider-credential analysis, connection lifecycle, and proposed API contract live in [PROVIDER_RUNTIME.md](../PROVIDER_RUNTIME.md).

### Option 1: Deployment-managed credentials

**Shape:** Provider keys are loaded from `inference/.env` or Docker secrets.

**Advantages:** Already supported and simple for a single operator or trusted deployment.

**Trade-offs:** Credentials are shared by all users, runtime model selection is limited, and rotation is operational rather than user-driven.

**Project fit:** Keep as an optional deployment default, not as the user-level credential architecture.

### Option 2: Short-lived server connections

**Shape:** The browser submits a credential once; FastAPI verifies it and stores it behind an opaque, user-bound connection ID with a TTL.

**Advantages:** Supports per-user selection without persistent secret storage and fits the current single-instance service.

**Trade-offs:** Requires authenticated inference endpoints, cleanup, expiry handling, and a documented single-instance limitation.

**Project fit:** Recommended first implementation.

### Option 3: Persistent encrypted credentials

**Shape:** Store per-user encrypted credentials or vault references for reuse across sessions.

**Advantages:** Better repeat-login experience and support for saved provider configurations.

**Trade-offs:** Adds key management, rotation, deletion, backup, audit, and breach-impact requirements.

**Project fit:** Later feature for a production workflow, preferably backed by an external vault.

## Phone Scanning and Desktop Handoff

The complete capture comparison is in [SCANNING_INTEGRATION_OPTIONS.md](../scanning/SCANNING_INTEGRATION_OPTIONS.md).

### Option 1: Mobile browser capture

**Shape:** Use a mobile file input with camera capture and reuse the existing upload path.

**Advantages:** Lowest implementation cost and broadest device coverage.

**Trade-offs:** The workflow remains on the phone and needs explicit multi-page grouping, orientation, and HEIC handling.

**Project fit:** Recommended for phone-only capture and a small first increment.

### Option 2: QR-paired web uploader

**Shape:** A desktop upload slot creates a short-lived session; a phone scans a QR code, uploads ordered pages, and the desktop receives the finalized document.

**Advantages:** Best web-native desktop handoff, no app-store dependency, and compatible with the existing React/FastAPI stack.

**Trade-offs:** Requires HTTPS, temporary storage, pairing authorization, cleanup, and new staging endpoints.

**Project fit:** Recommended for the full desktop-plus-phone workflow.

### Option 3: Native companion application

**Shape:** A Swift, Kotlin, or cross-platform mobile application uses native document-scanning APIs and uploads into an Exan session.

**Advantages:** Strongest camera and document-capture experience.

**Trade-offs:** Highest development and maintenance cost, platform-specific release work, and a larger product surface.

**Project fit:** Defer until web capture and pairing constraints justify native investment.

## Storage and Workflow State

### Option 1: Process memory

**Shape:** Store exams, answer keys, runtime connections, and temporary workflow data in the FastAPI process.

**Advantages:** No extra infrastructure and minimal implementation effort.

**Trade-offs:** Data disappears on restart, cannot be shared across replicas, and needs strict user ownership controls.

**Project fit:** Keep for the single-instance MVP only.

### Option 2: Shared TTL storage

**Shape:** Store temporary upload sessions and short-lived provider connections in a shared TTL-capable store.

**Advantages:** Supports multiple inference replicas while keeping temporary data bounded.

**Trade-offs:** Adds infrastructure, transport security, eviction behavior, and operational monitoring.

**Project fit:** Use when phone pairing or horizontal scaling requires shared ephemeral state.

### Option 3: Durable workflow storage

**Shape:** Persist exams, answer keys, grading runs, and result metadata in a database or object-storage-backed workflow store.

**Advantages:** Enables history, recovery, auditing, and asynchronous processing.

**Trade-offs:** Requires retention policies, access control, migrations, storage costs, and deletion workflows for exam data.

**Project fit:** Introduce when persistent exam history becomes a product requirement.

## Deployment and Networking

### Option 1: Docker Compose

**Shape:** Run nginx, webapp, inference, auth, and MongoDB together for local or small controlled deployments.

**Advantages:** Reproducible setup, clear service names, and straightforward local networking.

**Trade-offs:** Published service ports currently weaken nginx as a security boundary, and Compose is not a session scheduler.

**Project fit:** Current development and MVP deployment target.

### Option 2: Managed container deployment

**Shape:** Deploy services independently with managed networking, secrets, storage, logs, and scaling.

**Advantages:** Better availability, secret handling, observability, and replica management.

**Trade-offs:** More platform configuration and cost, plus a need for shared state and explicit service contracts.

**Project fit:** Production evolution after the authentication and persistence prerequisites are complete.
