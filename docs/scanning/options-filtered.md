# Filtered Phone Scanning Options

This comparison evaluates only options 3, 4, and 5 against the requested workflow:

- The user works in Exan from a PC.
- The phone is used only to capture and upload pictures.
- The solution remains a browser-based webapp across Windows, macOS, iOS, and Android.
- No native mobile or desktop application is developed.

## Evaluation Matrix

Scores are from 1 (poor fit) to 5 (strong fit). Higher implementation score means lower complexity.

| Criterion | Weight | 3. QR-paired web uploader | 4. Installable PWA scanner | 5. WebRTC peer transfer |
| --- | ---: | ---: | ---: | ---: |
| PC-first desktop handoff | 30% | 5 | 5 | 5 |
| Phone capture without native app | 20% | 5 | 5 | 5 |
| Windows, macOS, iOS, Android compatibility | 20% | 5 | 5 | 3 |
| Transfer reliability | 15% | 5 | 4 | 2 |
| Implementation and operational simplicity | 15% | 4 | 3 | 2 |
| **Weighted result** | **100%** | **4.8** | **4.3** | **3.5** |

## Assessment

| Option | Arguments |
| --- | --- |
| **3. QR-paired web uploader** | Best fit. The PC creates a short-lived session and QR code; the phone opens a minimal browser upload page. Files are transferred through the server, making pairing, retries, document grouping, authorization, and cross-network use manageable. It requires a phone-specific upload route, but not a complete mobile version of Exan. |
| **4. Installable PWA scanner** | Good follow-up to option 3, but unnecessary initially. Installation, service workers, IndexedDB, offline drafts, and background retry add complexity without improving the required PC workflow enough to justify starting here. |
| **5. WebRTC peer transfer** | Technically compatible, but a poor fit for the MVP. It requires signaling, connection management, STUN/TURN infrastructure, chunking, retries, and handling network or browser suspension. Reliability and cross-platform behavior are weaker than server-mediated upload. |

## Recommendation

Choose **option 3: QR-paired web uploader**.

Implement only a focused phone capture/upload route, not a second full mobile application. The PC remains the primary interface, while the phone scans a QR code, uploads ordered pages, and returns the finalized document to the active desktop upload slot. Add PWA capabilities later only if offline capture or interrupted-upload recovery becomes a demonstrated need.
