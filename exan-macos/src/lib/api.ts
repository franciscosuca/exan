import type { Connection } from "./bridge";
import type {
  AnswerView,
  CatalogModel,
  Grouping,
  KeyItem,
  PhoneTarget,
  PhoneView,
  PullView,
  RuntimeView,
  SessionView,
  Settings,
  Updated,
} from "./types";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

export class Api {
  private readonly connection: Connection;

  constructor(connection: Connection) {
    this.connection = connection;
  }

  async raw(path: string, init: RequestInit = {}): Promise<Response> {
    const headers = new Headers(init.headers);
    headers.set("Authorization", "Bearer " + this.connection.token);
    let response: Response;
    try {
      response = await fetch(this.connection.baseUrl + path, { ...init, headers });
    } catch (error) {
      if (init.signal?.aborted) throw error;
      throw new ApiError(0, "engine_unreachable", "The local engine is not reachable.");
    }
    if (!response.ok) {
      let code = `http_${response.status}`;
      let message = response.statusText || "Request failed.";
      try {
        const body = (await response.json()) as { detail?: string; code?: string };
        code = body.code ?? code;
        message = body.detail ?? message;
      } catch {
        // the body was not JSON
      }
      throw new ApiError(response.status, code, message);
    }
    return response;
  }

  private async json<T>(path: string, init: RequestInit = {}): Promise<T> {
    return (await (await this.raw(path, init)).json()) as T;
  }

  private send<T>(method: string, path: string, body?: unknown): Promise<T> {
    return this.json<T>(path, {
      method,
      headers: body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  }

  private upload(path: string, files: File[], fields: Record<string, string> = {}): Promise<Updated> {
    const form = new FormData();
    for (const [name, value] of Object.entries(fields)) form.append(name, value);
    for (const file of files) form.append("files", file, file.name);
    return this.json<Updated>(path, { method: "POST", body: form });
  }

  health = () => this.json<{ status: string; version: string }>("/health");
  session = (since?: number, wait = 0, signal?: AbortSignal) =>
    this.json<SessionView>(since === undefined ? "/session" : `/session?since=${since}&wait=${wait}`, { signal });
  resetSession = () => this.send<Updated>("POST", "/session/reset");
  cancelJobs = () => this.send<Updated>("POST", "/jobs/cancel");

  settings = () => this.json<Settings>("/settings");
  saveSettings = (patch: Partial<Settings>) => this.send<Settings>("PUT", "/settings", patch);
  runtime = () => this.json<RuntimeView>("/runtime");
  catalog = () => this.json<CatalogModel[]>("/catalog");
  pull = (model: string) => this.send<PullView>("POST", "/runtime/pull", { model });
  cancelPull = () => this.send<PullView>("DELETE", "/runtime/pull");

  addKeyPages = (files: File[]) => this.upload("/key/pages", files);
  deleteKeyPage = (id: string) => this.send<Updated>("DELETE", `/key/pages/${encodeURIComponent(id)}`);
  saveKeyItems = (items: KeyItem[]) => this.send<Updated>("PUT", "/key/items", { items });
  keyFromText = (text: string, mode: "replace" | "append") => this.send<Updated>("POST", "/key/text", { text, mode });
  extractKey = () => this.send<Updated>("POST", "/key/extract");

  addParticipants = (files: File[], grouping: Grouping) => this.upload("/participants", files, { grouping });
  extractParticipants = (scope: "pending" | "all") => this.send<Updated>("POST", "/participants/extract", { scope });
  patchParticipant = (id: string, patch: { name?: string; answers?: AnswerView[] }) =>
    this.send<Updated>("PATCH", `/participants/${encodeURIComponent(id)}`, patch);
  override = (id: string, question: string, verdict: "correct" | "incorrect" | null) =>
    this.send<Updated>("PUT", `/participants/${encodeURIComponent(id)}/override`, { question, verdict });
  addParticipantPages = (id: string, files: File[]) =>
    this.upload(`/participants/${encodeURIComponent(id)}/pages`, files);
  deleteParticipantPage = (id: string, pageId: string) =>
    this.send<Updated>("DELETE", `/participants/${encodeURIComponent(id)}/pages/${encodeURIComponent(pageId)}`);
  deleteParticipant = (id: string) => this.send<Updated>("DELETE", `/participants/${encodeURIComponent(id)}`);
  extractParticipant = (id: string) => this.send<Updated>("POST", `/participants/${encodeURIComponent(id)}/extract`);

  image = async (pageId: string, size: "thumb" | "full"): Promise<Blob> =>
    (await this.raw(`/images/${encodeURIComponent(pageId)}?size=${size}`)).blob();
  exportCsv = async (kind: "summary" | "detail", lang: "de" | "en"): Promise<string> =>
    (await this.raw(`/export.csv?kind=${kind}&lang=${lang}`)).text();

  phone = () => this.json<PhoneView>("/phone");
  startPhone = (target: PhoneTarget) => this.send<PhoneView>("POST", "/phone/start", { target });
  phoneTarget = (target: PhoneTarget) => this.send<PhoneView>("POST", "/phone/target", { target });
  stopPhone = () => this.send<PhoneView>("POST", "/phone/stop");
}
