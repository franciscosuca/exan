import { invoke, isTauri } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";

export type EngineState = "starting" | "ready" | "failed" | "stopped";

export interface EngineStatus {
  state: EngineState;
  port: number | null;
  token: string | null;
  error: string | null;
  restarts: number;
}

export interface Connection {
  baseUrl: string;
  token: string;
}

export const inDesktopApp = (): boolean => isTauri();

/** Development without the desktop shell: run the engine yourself and point Vite at it. */
function devConnection(): Connection | null {
  const url = import.meta.env.VITE_EXAN_API_URL as string | undefined;
  const token = import.meta.env.VITE_EXAN_TOKEN as string | undefined;
  if (!url || !token) return null;
  return { baseUrl: url.replace(/\/+$/, ""), token };
}

export function connectionFrom(status: EngineStatus): Connection | null {
  if (status.state !== "ready" || !status.port || !status.token) return null;
  return { baseUrl: `http://127.0.0.1:${status.port}/api`, token: status.token };
}

/** Calls `onStatus` with the engine status now and whenever it changes. Returns an unsubscribe function. */
export function watchEngine(onStatus: (status: EngineStatus, connection: Connection | null) => void): () => void {
  if (!inDesktopApp()) {
    const connection = devConnection();
    onStatus(
      connection
        ? { state: "ready", port: null, token: connection.token, error: null, restarts: 0 }
        : {
            state: "failed",
            port: null,
            token: null,
            error: "Set VITE_EXAN_API_URL and VITE_EXAN_TOKEN (see README) or start the desktop app.",
            restarts: 0,
          },
      connection,
    );
    return () => {};
  }
  let active = true;
  let unlisten: (() => void) | null = null;
  const deliver = (status: EngineStatus) => {
    if (active) onStatus(status, connectionFrom(status));
  };
  void listen<EngineStatus>("sidecar-status", (event) => deliver(event.payload)).then((stop) => {
    if (active) unlisten = stop;
    else stop();
    void invoke<EngineStatus>("engine_status").then(deliver);
  });
  return () => {
    active = false;
    unlisten?.();
  };
}

export async function restartEngine(): Promise<void> {
  if (inDesktopApp()) await invoke("restart_engine");
}

export async function openHelp(topic: "ollama" | "lmstudio" | "models"): Promise<void> {
  if (inDesktopApp()) {
    await invoke("open_help", { topic });
    return;
  }
  const urls = {
    ollama: "https://ollama.com/download",
    lmstudio: "https://lmstudio.ai/download",
    models: "https://huggingface.co/blog/ocr-open-models",
  };
  window.open(urls[topic], "_blank", "noopener,noreferrer");
}

/** Saves text through the native save dialog (desktop) or a download (browser). Returns false when cancelled. */
export async function saveTextFile(fileName: string, contents: string): Promise<boolean> {
  if (inDesktopApp()) {
    const path = await invoke<string | null>("save_text_file", { fileName, contents });
    return path !== null;
  }
  const url = URL.createObjectURL(new Blob([contents], { type: "text/csv;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  return true;
}
