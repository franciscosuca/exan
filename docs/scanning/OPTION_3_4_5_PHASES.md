# Implementation Phases for Scanning Options 3, 4, and 5

This document still compares the filtered phone-scanning options at a high level, but the implementation planning below is now focused on **option 3**, which is the recommended first path for Exan:

- **Option 3:** QR-paired web uploader
- **Option 4:** Installable PWA scanner
- **Option 5:** WebRTC peer transfer

It focuses on the phases required to implement option 3 in Exan, with emphasis on **complexity**, **integration impact**, and likely **token usage** for AI-assisted implementation.

## Comparison Summary

| Option | Core idea | Complexity | Integration impact | Expected token usage | Best fit |
| --- | --- | --- | --- | --- | --- |
| **3. QR-paired web uploader** | Desktop creates a temporary session, phone uploads through a mobile web page, server stages the files, desktop receives the result | Medium | Medium across webapp, inference, auth, and temporary storage | Medium | Best default choice for the current product |
| **4. Installable PWA scanner** | Option 3 plus installable scanner shell, local draft persistence, and retry/offline behavior | Medium-high | Medium-high, mostly on webapp plus the same backend work as option 3 | Medium-high | Good follow-up if interrupted uploads or draft recovery become important |
| **5. WebRTC peer transfer** | Desktop and phone pair, then transfer pages directly over a peer connection | High | High across webapp, inference signaling, networking, and ops | High | Only suitable if server-side staging must be minimized |

## Option 3 protocol choice

| Question | Answer |
| --- | --- |
| **Does option 3 need WebSockets?** | **No.** The first implementation can work with normal **HTTPS requests** for session creation, page upload, and finalization, plus **desktop polling** for status updates. |
| **What is the most likely first protocol?** | **REST-style HTTPS endpoints** between React and FastAPI. |
| **How does the desktop learn the phone is done?** | The desktop can **poll a session-status endpoint** every few seconds until the session changes state. |
| **When would WebSockets be useful?** | Only if Exan later needs richer real-time updates, bidirectional presence, or a more interactive pairing flow. |

So for the first implementation of **option 3**, the recommended stack is:

1. **HTTPS + JSON/FormData APIs** for pairing, upload, and finalize
2. **QR code** that encodes the short-lived phone session URL or token
3. **Polling first**, with **SSE optional later**
4. **No WebSocket requirement**

## Option 3 backend session lifecycle

The backend session is the core of option 3. It is a **short-lived upload container** owned by the signed-in desktop user and tied to one active upload slot.

| Step | Backend behavior | Result |
| --- | --- | --- |
| **1. Desktop creates session** | The desktop calls a new authenticated FastAPI endpoint such as `POST /api/phone-scanning/sessions` with context like workflow type, upload slot, and file mode. | FastAPI creates a session record with `session_id`, `pair_token`, `status`, `expires_at`, and owner metadata. |
| **2. Backend stores session** | The session record is written into a short-lived repository, ideally with TTL semantics even if the first version starts in memory. | Exan can track whether the session is `waiting_for_phone`, `uploading`, `finalized`, `cancelled`, or `expired`. |
| **3. Desktop shows QR** | The backend returns a short-lived phone URL or redeemable token. | The desktop renders a QR code for the phone to open. |
| **4. Phone claims session** | The phone opens the QR link and redeems the token through HTTPS. The backend verifies the token, expiry, and session status. | The phone is attached only to that upload session, without needing WebSockets. |
| **5. Phone uploads pages** | The phone sends ordered pages with multipart uploads. FastAPI validates type, size, page order, and session ownership, then stages the files. | The session status moves to `uploading` and then to `ready_to_finalize` when enough data exists. |
| **6. Phone finalizes document** | The phone sends a finalize request after reordering/confirming pages. The backend assembles or stages the logical document and stores result metadata on the session. | The session status becomes `finalized`. |
| **7. Desktop consumes result** | The desktop keeps polling the session status endpoint until it sees `finalized`, then requests the staged document metadata or triggers the existing upload pipeline. | The existing Exan flow can continue without a persistent socket connection. |

### Why polling is enough for the first version

Polling works because option 3 does not require continuous peer-to-peer coordination. The desktop only needs to know whether the session has moved from one coarse state to another.

A simple implementation would look like this:

1. The desktop creates a session.
2. The desktop calls `GET /api/phone-scanning/sessions/{session_id}` every 2 to 5 seconds.
3. FastAPI returns a small JSON payload such as:
   - `status`
   - `expires_at`
   - `uploaded_page_count`
   - `document_ready`
   - `error`
4. When `status === "finalized"`, the desktop stops polling and continues with the normal analysis flow.
5. If the session expires or is cancelled, the desktop stops polling and shows a retry action.

This keeps the architecture simple because:

- there is **no persistent connection** to maintain
- nginx and FastAPI already support normal request/response traffic
- retries are straightforward because each poll is independent
- the session state remains authoritative on the server

## Option 3 implementation phases mapped to the repository

The table below matches the option 3 plan to the **real phases** and to the **specific files** most likely to be changed or created in this repository.

| Phase | Goal | Files to modify | Files to create | Notes |
| --- | --- | --- | --- | --- |
| **1. Desktop entry point and pairing UI** | Add a **Scan with phone** action to the existing upload workflow and display the QR/session state. | `/home/runner/work/exan/exan/webapp/src/components/FileDropzone.tsx`, `/home/runner/work/exan/exan/webapp/src/components/ExamComparison.tsx`, `/home/runner/work/exan/exan/webapp/src/components/BatchEvaluation.tsx` | `/home/runner/work/exan/exan/webapp/src/components/PhonePairingPanel.tsx` | This phase is where the desktop user starts the session. |
| **2. Frontend API and polling client** | Add session creation, status polling, cancel, phone upload, and finalize requests. | `/home/runner/work/exan/exan/webapp/src/lib/api.ts`, `/home/runner/work/exan/exan/webapp/src/auth.api.ts` | optional `/home/runner/work/exan/exan/webapp/src/lib/phoneScanning.ts` | Polling belongs here because the desktop needs a lightweight status loop, not WebSockets. |
| **3. Phone scanner route and page flow** | Add the mobile route opened from the QR code, with capture/review/finalize behavior. | `/home/runner/work/exan/exan/webapp/src/App.tsx` | `/home/runner/work/exan/exan/webapp/src/pages/PhoneScannerPage.tsx` | This is the phone-only browser view for option 3. |
| **4. Session API registration** | Register dedicated FastAPI routes for upload-session creation, claim, page upload, status, cancel, and finalize. | `/home/runner/work/exan/exan/inference/app/main.py`, `/home/runner/work/exan/exan/inference/app/api/routes/__init__.py` | `/home/runner/work/exan/exan/inference/app/api/routes/phone_scanning.py` | Keep this separate from the existing exam upload endpoints. |
| **5. Session service and repository** | Implement the session lifecycle, token validation, staging, expiry, and cleanup behavior. | `/home/runner/work/exan/exan/inference/app/api/dependencies.py` | `/home/runner/work/exan/exan/inference/app/services/phone_scanning.py`, `/home/runner/work/exan/exan/inference/app/repositories/upload_session_repository.py` | This is the backend core of option 3. |
| **6. Deployment and reachability** | Ensure the phone can reach the app, uploads fit limits, and the QR target is valid outside localhost-only development. | `/home/runner/work/exan/exan/webapp/nginx.conf`, `/home/runner/work/exan/exan/docker-compose.yml` | none required | HTTPS reachability matters more here than real-time transport. |
| **7. Validation and tests** | Validate pairing, expiry, upload ordering, finalize behavior, and desktop polling. | `/home/runner/work/exan/exan/webapp/src/test/App.test.tsx` and the existing inference test area | likely new tests under `/home/runner/work/exan/exan/inference/tests/` | The first validation target is the session lifecycle, not live socket behavior. |

## Smallest realistic file set for option 3

If implemented with the **smallest viable scope**, the most likely first-pass changes would be:

- **Modify**
  - `/home/runner/work/exan/exan/webapp/src/components/FileDropzone.tsx`
  - `/home/runner/work/exan/exan/webapp/src/components/ExamComparison.tsx`
  - `/home/runner/work/exan/exan/webapp/src/components/BatchEvaluation.tsx`
  - `/home/runner/work/exan/exan/webapp/src/lib/api.ts`
  - `/home/runner/work/exan/exan/webapp/src/auth.api.ts`
  - `/home/runner/work/exan/exan/webapp/src/App.tsx`
  - `/home/runner/work/exan/exan/inference/app/main.py`
  - `/home/runner/work/exan/exan/inference/app/api/routes/__init__.py`
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
