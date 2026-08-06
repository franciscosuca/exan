# Selection Criteria for Option 3

This document summarizes the most important criteria discussed for choosing **option 3: QR-paired web uploader** as the preferred phone-scanning path for Exan.

## Decision Criteria

| Criterion | Why it matters for Exan | Why option 3 fits |
| --- | --- | --- |
| **Desktop-first workflow** | The user wants to keep working from the PC and use the phone only as the scanner. | Option 3 keeps the desktop as the main workflow owner and uses the phone as a temporary capture device. |
| **Browser-first product direction** | Exan is currently a React webapp with FastAPI and Docker Compose, not a native desktop or mobile product. | Option 3 stays inside the current web architecture and does not require Electron, Tauri, Wails, or native mobile apps. |
| **Cross-platform reach** | The solution should remain usable across Windows, macOS, Android, and iPhone browsers. | Option 3 works with ordinary phone browsers and avoids OS-specific transport features. |
| **Implementation complexity** | A first version should be achievable without introducing unnecessary real-time or native infrastructure. | Option 3 can be built with HTTPS endpoints, QR pairing, temporary storage, and polling. |
| **Integration cost** | The best option should reuse existing upload flows as much as possible. | Option 3 can feed the current React upload entry points and existing FastAPI processing pipeline after staging. |
| **Reliability** | Uploads need to behave predictably across different networks and school/home environments. | Server-mediated transfer is more reliable than direct peer transfer and easier to retry. |
| **Token usage for implementation** | The planning goal includes choosing an option that is not unnecessarily expensive to implement with AI assistance. | Option 3 stays focused on ordinary frontend/backend CRUD-style work instead of deeper networking or native integration. |
| **No WebSocket requirement** | Avoiding unnecessary real-time protocols reduces moving parts in the first version. | Option 3 can work with polling first and only add SSE later if needed. |
| **Security and ownership control** | A phone-upload session must belong to the authenticated desktop user and expire safely. | Option 3 has a clear model: authenticated session creation, short-lived pair token, expiry, and server-side state checks. |
| **Future extensibility** | The chosen MVP should allow later upgrades without forcing a rewrite. | Option 3 can later evolve into option 4 by adding PWA capabilities on top of the same session model. |

## Criteria that make option 3 stronger than the alternatives

| Compared with | Why option 3 is preferable |
| --- | --- |
| **Option 4** | Option 4 is a good extension, but it adds service workers, install behavior, offline drafts, and retry complexity before the core workflow is proven. |
| **Option 5** | Option 5 adds signaling, peer connection management, STUN/TURN decisions, and lower reliability across restrictive networks. |
| **Desktop-app alternatives** | Tauri/Wails/Electron would push Exan toward a different product model with packaging, distribution, and native integration work. |

## Recommended decision rule

Choose **option 3** if the priority order is:

1. Keep Exan browser-first
2. Let the PC remain the main workflow
3. Avoid WebSockets and peer-to-peer networking in the MVP
4. Reuse the current React + FastAPI architecture
5. Leave room for PWA improvements later
