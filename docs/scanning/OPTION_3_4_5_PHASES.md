# Implementation Phases for Scanning Options 3, 4, and 5

This document is a high-level planning aid for deciding between the filtered phone-scanning options:

- **Option 3:** QR-paired web uploader
- **Option 4:** Installable PWA scanner
- **Option 5:** WebRTC peer transfer

It focuses on the phases required to implement each option in Exan, with emphasis on **complexity**, **integration impact**, and likely **token usage** for AI-assisted implementation.

## Comparison Summary

| Option | Core idea | Complexity | Integration impact | Expected token usage | Best fit |
| --- | --- | --- | --- | --- | --- |
| **3. QR-paired web uploader** | Desktop creates a temporary session, phone uploads through a mobile web page, server stages the files, desktop receives the result | Medium | Medium across webapp, inference, auth, and temporary storage | Medium | Best default choice for the current product |
| **4. Installable PWA scanner** | Option 3 plus installable scanner shell, local draft persistence, and retry/offline behavior | Medium-high | Medium-high, mostly on webapp plus the same backend work as option 3 | Medium-high | Good follow-up if interrupted uploads or draft recovery become important |
| **5. WebRTC peer transfer** | Desktop and phone pair, then transfer pages directly over a peer connection | High | High across webapp, inference signaling, networking, and ops | High | Only suitable if server-side staging must be minimized |

## Option 3 protocol choice

| Question | Answer |
| --- | --- |
| **Does option 3 need WebSockets?** | **No.** The simplest version can work with normal **HTTPS requests** for session creation, page upload, and finalization, plus **desktop polling** for status updates. |
| **What is the most likely first protocol?** | **REST-style HTTPS endpoints** between React and FastAPI. |
| **How does the desktop learn the phone is done?** | Start with **polling** from the desktop. **SSE** is a reasonable later improvement. |
| **When would WebSockets be useful?** | Only if Exan later needs richer real-time updates, bidirectional presence, or a more interactive pairing flow. |

So for the first implementation of **option 3**, the recommended stack is:

1. **HTTPS + JSON/FormData APIs** for pairing, upload, and finalize
2. **QR code** that encodes the short-lived phone session URL or token
3. **Polling first**, with **SSE optional later**
4. **No WebSocket requirement**

## High-Level Implementation Phases

| Phase | Option 3: QR-paired web uploader | Option 4: Installable PWA scanner | Option 5: WebRTC peer transfer |
| --- | --- | --- | --- |
| **1. Product and workflow definition** | Define desktop upload-slot behavior, pairing lifetime, page ordering, finalize/cancel states, and ownership rules | Define the same workflow as option 3 plus install, resume, offline, and retry expectations | Define pairing, signaling, transfer ownership, failure recovery, and fallback behavior when peer connection fails |
| **2. Frontend desktop integration** | Add a **Scan with phone** entry point in the existing React upload flow, session creation UI, QR display, and status updates | Reuse option 3 desktop flow with PWA-specific scanner status and retry states | Add QR/signaling UI, connection state, transfer progress, failure handling, and likely a server fallback path |
| **3. Frontend phone experience** | Build a mobile web route for capture, page review, reorder, upload, and finalize | Build the same phone route plus app-like install flow, local drafts, and resume UX | Build a phone capture route plus peer-connection lifecycle, chunk send/retry, and reconnection handling |
| **4. Backend/API work** | Add short-lived session APIs, staged upload/finalize endpoints, validation, expiry, and conversion into the existing processing pipeline | Mostly the same backend contract as option 3, with extra endpoints or state for resumable drafts if needed | Add signaling endpoints, transfer authorization, desktop-side finalize handling, and still keep a path into the existing processing pipeline |
| **5. Persistence and storage** | Introduce TTL session metadata and temporary file/document staging | Add server staging from option 3 plus client-side storage strategy such as IndexedDB | Minimize server-side staging, but still store signaling/session metadata and possibly fallback or partial-transfer state |
| **6. Auth and security hardening** | Bind sessions to authenticated desktop users, limit token scope, enforce expiry, and protect staged documents | Same as option 3 plus protect locally cached draft data and service-worker behavior | Same as option 3 plus secure signaling, peer authorization, integrity checks, and TURN-related exposure |
| **7. Deployment and networking** | Ensure both phone and desktop can reach the app over HTTPS and that temporary uploads fit current deployment limits | Same as option 3 plus service-worker deployment/versioning and mobile storage constraints | Add HTTPS plus STUN/TURN decisions, firewall/NAT considerations, and relay-cost/reliability planning |
| **8. Validation and rollout** | Test pairing, upload ordering, cancellation, expiry, and multi-document flows | Test option 3 flows plus install, update, offline draft, and retry behavior | Test connectivity across browsers/networks, suspension/reconnect cases, and degraded/fallback flows |

## Per-Option Planning Notes

| Option | What makes it manageable | What makes it expensive | Suggested implementation order |
| --- | --- | --- | --- |
| **3. QR-paired web uploader** | Reuses the existing browser-first architecture and keeps transfer logic server-mediated | Needs new session APIs, temporary storage, authorization, and desktop/phone coordination | Start here first |
| **4. Installable PWA scanner** | Builds directly on option 3 instead of replacing it | Adds service worker, client-side persistence, install/update behavior, and retry complexity | Only after option 3 proves the workflow |
| **5. WebRTC peer transfer** | Reduces server storage during successful direct transfer | Adds the most networking, connection-state, and reliability complexity; TURN can erase the main benefit | Consider only if policy rules reject staged uploads |

## Likely files for option 3 in the current repository

The table below maps **option 3** onto the repository as it exists today. It is not a final implementation plan, but it shows the most likely files to **modify** or **create**.

| Area | Likely files to modify | Likely files to create | Why |
| --- | --- | --- | --- |
| **Desktop upload entry points** | `/home/runner/work/exan/exan/webapp/src/components/FileDropzone.tsx`, `/home/runner/work/exan/exan/webapp/src/components/ExamComparison.tsx`, `/home/runner/work/exan/exan/webapp/src/components/BatchEvaluation.tsx` | `/home/runner/work/exan/exan/webapp/src/components/PhonePairingPanel.tsx` | Add a **Scan with phone** action next to the existing browser upload flow. |
| **Frontend API client** | `/home/runner/work/exan/exan/webapp/src/lib/api.ts` | none required if kept in one file, or `/home/runner/work/exan/exan/webapp/src/lib/phoneScanning.ts` if split out | Add calls for session creation, phone upload, finalize, cancel, and status polling. |
| **Phone scanner route/UI** | `/home/runner/work/exan/exan/webapp/src/App.tsx` | `/home/runner/work/exan/exan/webapp/src/pages/PhoneScannerPage.tsx` | Add a phone-only route/view that the QR code opens. |
| **Frontend auth integration** | `/home/runner/work/exan/exan/webapp/src/auth.api.ts` | none required | Reuse the saved token or extend auth helpers so the desktop-owned pairing session is authenticated. |
| **Inference route registration** | `/home/runner/work/exan/exan/inference/app/main.py`, `/home/runner/work/exan/exan/inference/app/api/routes/__init__.py` | `/home/runner/work/exan/exan/inference/app/api/routes/phone_scanning.py` | Register a dedicated FastAPI router for temporary upload sessions instead of overloading the existing exam endpoints. |
| **Workflow/service layer** | `/home/runner/work/exan/exan/inference/app/api/dependencies.py` | `/home/runner/work/exan/exan/inference/app/services/phone_scanning.py` | Encapsulate session creation, pairing validation, staged uploads, finalization, and cleanup. |
| **Temporary state / repository** | none required if first pass is in-memory, but existing repository wiring is in `/home/runner/work/exan/exan/inference/app/api/dependencies.py` | likely `/home/runner/work/exan/exan/inference/app/repositories/upload_session_repository.py` | Option 3 needs short-lived session state separate from the current exam repository. |
| **Auth boundary** | `/home/runner/work/exan/exan/auth/server.ts`, `/home/runner/work/exan/exan/auth/middleware/auth.middleware.ts` if shared validation stays in the auth service | possibly a new shared token-validation path, depending on architecture | Ensure phone session creation is tied to the signed-in desktop user and cannot be claimed by another user. |
| **Deployment / reachability** | `/home/runner/work/exan/exan/webapp/nginx.conf`, `/home/runner/work/exan/exan/docker-compose.yml` | none required | Phone access requires a reachable HTTPS deployment path and request-size/time-limit review. |
| **Tests** | `/home/runner/work/exan/exan/webapp/src/test/App.test.tsx` and the existing inference test area | likely new tests under `/home/runner/work/exan/exan/inference/tests/` for session APIs | Validate pairing, expiry, upload ordering, and finalize behavior. |

### Smallest realistic file set

If implemented with the **smallest viable scope**, the most likely first-pass changes would be:

- **Modify**
  - `/home/runner/work/exan/exan/webapp/src/components/FileDropzone.tsx`
  - `/home/runner/work/exan/exan/webapp/src/components/ExamComparison.tsx`
  - `/home/runner/work/exan/exan/webapp/src/lib/api.ts`
  - `/home/runner/work/exan/exan/webapp/src/App.tsx`
  - `/home/runner/work/exan/exan/inference/app/main.py`
  - `/home/runner/work/exan/exan/inference/app/api/dependencies.py`
  - `/home/runner/work/exan/exan/webapp/nginx.conf`
  - `/home/runner/work/exan/exan/docker-compose.yml`
- **Create**
  - `/home/runner/work/exan/exan/webapp/src/components/PhonePairingPanel.tsx`
  - `/home/runner/work/exan/exan/webapp/src/pages/PhoneScannerPage.tsx`
  - `/home/runner/work/exan/exan/inference/app/api/routes/phone_scanning.py`
  - `/home/runner/work/exan/exan/inference/app/services/phone_scanning.py`
  - `/home/runner/work/exan/exan/inference/app/repositories/upload_session_repository.py`

## Desktop-App Alternative Context

The issue discussion also mentioned desktop frameworks such as **[Wails](https://wails.io/docs/introduction/)** and **[Tauri](https://v2.tauri.app/start/)**. Those are better aligned with the separate desktop-app path already discussed in `OPTIONS.md` rather than with options 3, 4, or 5 themselves.

| If you want... | Better path |
| --- | --- |
| Keep Exan as a browser product and let the phone feed scans into the existing PC workflow | **Option 3** first, optionally **option 4** later |
| Build a managed desktop product with native OS integrations and a broader desktop roadmap | Re-evaluate the separate desktop-app option with **Tauri** or **Wails** |
| Avoid server-side temporary image staging even at the cost of reliability and complexity | **Option 5** |

## Recommendation for Decision-Making

| Priority | Best option |
| --- | --- |
| Lowest overall implementation risk | **Option 3** |
| Better resilience for interrupted mobile capture | **Option 4**, but only after option 3 |
| Lowest server-side staging footprint | **Option 5** |

For Exan's current architecture, **option 3 has the best balance of complexity, integration effort, and token usage**. **Option 4** is the most natural second step if the browser-based scanner needs draft recovery or offline tolerance. **Option 5** should remain a policy-driven alternative rather than the default implementation path.
