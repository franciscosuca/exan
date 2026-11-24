export type JobStatus = "idle" | "queued" | "processing" | "done" | "error";
export type Verdict = "correct" | "incorrect" | "review" | "missing";
export type Grouping = "file" | "page" | "single";
export type PhoneTarget = "key" | "participants";

export interface ErrorView {
  code: string;
  message: string;
}

export interface PageView {
  id: string;
  name: string;
  width: number;
  height: number;
  source: string;
}

export interface Progress {
  done: number;
  total: number;
}

export interface KeyItem {
  question: string;
  answer: string;
  points: number;
}

export interface KeyView {
  pages: PageView[];
  items: KeyItem[];
  status: JobStatus;
  error: ErrorView | null;
  progress: Progress;
  duplicates: string[];
  max_score: number;
}

export interface QuestionResult {
  question: string;
  key: string;
  expected: string;
  given: string;
  points: number;
  auto: Verdict;
  reason: string;
  override: "correct" | "incorrect" | null;
  final: Verdict;
  earned: number;
}

export interface AnswerView {
  question: string;
  answer: string;
}

export interface SheetResult {
  score: number;
  max_score: number;
  percent: number | null;
  counts: Record<Verdict, number>;
  questions: QuestionResult[];
  extra: AnswerView[];
}

export interface ParticipantView {
  id: string;
  number: number;
  name: string;
  pages: PageView[];
  answers: AnswerView[];
  status: JobStatus;
  error: ErrorView | null;
  progress: Progress;
  source: string;
  graded: boolean;
  result: SheetResult;
}

export interface QuestionStat {
  question: string;
  key: string;
  correct: number;
  review: number;
  missing: number;
  total: number;
  rate: number | null;
}

export interface Stats {
  graded: number;
  average: number | null;
  best: number | null;
  worst: number | null;
  pending_review: number;
  questions: QuestionStat[];
}

export interface SessionView {
  id: string;
  version: number;
  key: KeyView;
  participants: ParticipantView[];
  stats: Stats;
  jobs: { queued: number; running: boolean; current: { kind: string; target: string | null } | null };
  last_phone_upload: { id: string; target: PhoneTarget; pages: number; participants: number } | null;
  phone: { active: boolean; target: PhoneTarget; uploads: number };
}

export type RuntimeKind = "builtin" | "ollama" | "openai";

export interface Settings {
  runtime: RuntimeKind;
  ollama_url: string;
  openai_url: string;
  model: string;
  extraction_mode: "auto" | "structured" | "ocr";
  max_image_side: number;
  request_timeout: number;
  language: "de" | "en";
}

export interface ModelInfo {
  name: string;
  size: number | null;
  vision: boolean | null;
  family: string;
  parameters: string;
  quantization: string;
}

export interface PullView {
  state?: "running" | "done" | "error" | "cancelled";
  model?: string;
  status?: string;
  completed?: number | null;
  total?: number | null;
  error?: ErrorView | string | null;
}

export interface RuntimeView {
  kind: string;
  url: string;
  reachable: boolean;
  version: string | null;
  models: ModelInfo[];
  error: ErrorView | null;
  model: string;
  model_installed: boolean;
  pull: PullView;
}

export interface CatalogModel {
  name: string;
  label: string;
  params: string;
  download_gb: number;
  min_ram_gb: number;
  mode: string;
  recommended: boolean;
  notes: string;
  min_ollama: string;
}

/** A model of the built-in runtime (GET /models). */
export interface BuiltinModel {
  id: string;
  label: string;
  vendor: string;
  params: string;
  mode: "ocr" | "structured";
  recommended: boolean;
  license: string;
  homepage: string;
  min_ram_gb: number;
  download_bytes: number;
  downloaded_bytes: number;
  installed: boolean;
  notes: Partial<Record<"de" | "en", string>>;
  /** One line, used where space is short (installer page). */
  summary: Partial<Record<"de" | "en", string>>;
  source: string;
}

export interface PhoneView {
  active: boolean;
  target: PhoneTarget;
  port?: number;
  urls: { url: string; qr: string }[];
  uploads: number;
  expires_in?: number;
}

export interface UploadError {
  file: string;
  code: string;
  message: string;
}

export interface Updated {
  session: SessionView;
  errors?: UploadError[];
  created?: string[];
  queued?: number;
}
