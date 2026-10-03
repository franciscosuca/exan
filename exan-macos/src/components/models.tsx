import { useCallback, useEffect, useState } from "react";
import { Square } from "lucide-react";
import { useI18n, type Language } from "../lib/i18n";
import { useApp } from "../lib/store";
import type { BuiltinModel, PullView } from "../lib/types";
import { Button, formatNumber } from "./ui";

export const MODEL_SOURCE = "Hugging Face (huggingface.co)";

export function formatBytes(bytes: number, language: Language): string {
  return bytes >= 1e9 ? `${formatNumber(bytes / 1e9, language, 1)} GB` : `${formatNumber(bytes / 1e6, language, 0)} MB`;
}

/** Size, memory, notes and licence of a built-in model. */
export function ModelDetails({ model }: { model: BuiltinModel }) {
  const { t, language } = useI18n();
  return (
    <>
      <p className="text-xs text-muted">{t("modelMeta", { params: model.params, size: formatBytes(model.download_bytes, language), gb: model.min_ram_gb })}</p>
      <p className="mt-1 text-sm">{model.notes[language] ?? model.notes.en}</p>
      <p className="mt-1 text-xs text-muted">{t("modelLicense", { license: model.license, source: model.source })}</p>
    </>
  );
}

/** Follows a running model download by polling the engine once per second. */
export function usePull(initial: PullView | null | undefined, onFinished: (pull: PullView) => void) {
  const { api } = useApp();
  const [pull, setPull] = useState<PullView | null>(initial ?? null);
  // The runtime state may arrive after mounting (Settings loads it itself): pick up a running download.
  useEffect(() => {
    if (initial?.state === "running") setPull(initial);
  }, [initial]);
  const running = pull?.state === "running";
  useEffect(() => {
    if (!running) return;
    let active = true;
    const timer = setInterval(() => {
      void api
        .runtime()
        .then((runtime) => {
          if (!active) return;
          setPull(runtime.pull);
          if (runtime.pull.state !== "running") onFinished(runtime.pull);
        })
        .catch(() => undefined);
    }, 1000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [api, running, onFinished]);
  return { pull, setPull, running };
}

export function PullProgress({ pull, label, size, onCancel }: { pull: PullView; label: string; size?: number; onCancel: () => void }) {
  const { t, language } = useI18n();
  const total = pull.total ?? size ?? 0; // the size is only reported once the download has started
  const done = Math.min(pull.completed ?? 0, total);
  const percent = total ? Math.floor((done / total) * 100) : 0;
  return (
    <div className="flex flex-col gap-2" role="status" data-testid="pull-progress">
      <div className="h-2 w-full bg-line" aria-hidden="true">
        <div className="h-2 bg-accent transition-[width]" style={{ width: `${percent}%` }} />
      </div>
      <div className="flex items-center justify-between gap-3 text-sm">
        <span>{t("setupProgress", { model: label, done: formatBytes(done, language), total: formatBytes(total, language), percent })}</span>
        <Button variant="ghost" onClick={onCancel}>
          <Square size={14} /> {t("cancel")}
        </Button>
      </div>
    </div>
  );
}

export function pullError(pull: PullView | null): string | null {
  if (pull?.state !== "error" || !pull.error) return null;
  return typeof pull.error === "string" ? pull.error : pull.error.message;
}

/** Loads the built-in model list; `reload` refreshes it (after downloads or removals). */
export function useBuiltinModels() {
  const { api, run } = useApp();
  const [models, setModels] = useState<BuiltinModel[] | null>(null);
  const reload = useCallback(async () => {
    const list = await run(() => api.models());
    if (list) setModels(list);
    return list;
  }, [api, run]);
  useEffect(() => {
    void reload();
  }, [reload]);
  return { models, setModels, reload };
}
