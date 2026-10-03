import { useCallback, useEffect, useState } from "react";
import { Download, ExternalLink, RefreshCw, Square } from "lucide-react";
import { confirmAction, openHelp } from "../lib/bridge";
import { useI18n, type Language } from "../lib/i18n";
import { useApp } from "../lib/store";
import type { CatalogModel, RuntimeKind, RuntimeView, Settings } from "../lib/types";
import { MODEL_SOURCE, ModelDetails, PullProgress, formatBytes, pullError, useBuiltinModels, usePull } from "./models";
import { Button, Label, Modal } from "./ui";

function percent(completed?: number | null, total?: number | null): string {
  return completed && total ? `${Math.floor((completed / total) * 100)} %` : "";
}

export function useRuntime() {
  const { api } = useApp();
  const [runtime, setRuntime] = useState<RuntimeView | null>(null);
  const refresh = useCallback(async () => {
    try {
      setRuntime(await api.runtime());
    } catch {
      setRuntime(null);
    }
  }, [api]);
  useEffect(() => {
    void refresh();
  }, [refresh]);
  return { runtime, refresh };
}

const RUNTIMES: { kind: RuntimeKind; label: "runtimeBuiltin" | "runtimeOllama" | "runtimeOpenAI" }[] = [
  { kind: "builtin", label: "runtimeBuiltin" },
  { kind: "ollama", label: "runtimeOllama" },
  { kind: "openai", label: "runtimeOpenAI" },
];

/** Models of the built-in runtime: download (after consent), use and remove. */
function BuiltinModelsSection({ active, runtime, onUse, onChanged }: { active: string; runtime: RuntimeView | null; onUse: (id: string) => Promise<void>; onChanged: () => void }) {
  const { t, language } = useI18n();
  const { api, run } = useApp();
  const { models, setModels, reload } = useBuiltinModels();
  const [consent, setConsent] = useState(false);
  const finished = useCallback(() => {
    void reload();
    onChanged();
  }, [reload, onChanged]);
  const { pull, setPull, running } = usePull(runtime?.pull, finished);
  if (!models) return null;
  const error = pullError(pull);

  const download = async (id: string) => {
    const started = await run(() => api.pull(id));
    if (started) setPull(started);
  };
  const remove = async (id: string, label: string, bytes: number) => {
    if (!(await confirmAction(t("deleteModelConfirm", { model: label, size: formatBytes(bytes, language) }), t("deleteModel"), t("cancel")))) return;
    const list = await run(() => api.deleteModel(id));
    if (list) setModels(list);
    onChanged();
  };

  return (
    <section className="flex flex-col gap-2">
      <Label>{t("builtinModels")}</Label>
      <label className="flex items-start gap-2 text-xs">
        <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} className="mt-0.5" />
        <span>{t("consentModels", { source: MODEL_SOURCE })}</span>
      </label>
      {running && pull && (
        <PullProgress pull={pull} label={models.find((m) => m.id === pull.model)?.label ?? pull.model ?? ""} size={models.find((m) => m.id === pull.model)?.download_bytes} onCancel={() => void run(() => api.cancelPull()).then((next) => next && setPull(next))} />
      )}
      {error && <p className="text-xs text-danger">{error}</p>}
      <ul className="flex flex-col gap-2" data-testid="builtin-models">
        {models.map((model) => (
          <li key={model.id} className="flex items-start gap-3 border-hair border-line bg-white p-3">
            <div className="flex-1">
              <p className="font-semibold">
                {model.label} <span className="text-xs font-normal text-muted">{model.vendor}</span>
                {model.recommended && <span className="ml-2 bg-accent px-1.5 py-0.5 text-[10px] text-white uppercase">{t("recommended")}</span>}
                {model.installed && <span className="ml-2 text-xs text-accent">{t("modelInstalled")}</span>}
              </p>
              <ModelDetails model={model} />
            </div>
            <div className="flex flex-col items-end gap-1">
              {model.installed && active === model.id ? (
                <span className="text-xs font-semibold">{t("inUse")}</span>
              ) : model.installed ? (
                <Button onClick={() => void onUse(model.id)}>{t("use")}</Button>
              ) : (
                <Button disabled={!consent || running} onClick={() => void download(model.id)}>
                  <Download size={14} /> {t("download")}
                </Button>
              )}
              {model.installed && (
                <Button variant="danger" disabled={running} onClick={() => void remove(model.id, model.label, model.download_bytes)}>
                  {t("deleteModel")}
                </Button>
              )}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function SettingsPanel({ onClose, onChanged }: { onClose: () => void; onChanged: () => void }) {
  const { t, language, setLanguage } = useI18n();
  const { api, run } = useApp();
  const [settings, setSettings] = useState<Settings | null>(null);
  const [catalog, setCatalog] = useState<CatalogModel[]>([]);
  const { runtime, refresh } = useRuntime();
  const pulling = runtime?.pull.state === "running";

  useEffect(() => {
    void run(async () => {
      const [loaded, models] = await Promise.all([api.settings(), api.catalog()]);
      setSettings(loaded);
      setCatalog(models);
    });
  }, [api, run]);

  const builtin = settings?.runtime === "builtin";
  useEffect(() => {
    if (!pulling || builtin) return;
    const timer = setInterval(() => void refresh(), 1000);
    return () => clearInterval(timer);
  }, [pulling, builtin, refresh]);

  const save = async (patch: Partial<Settings>) => {
    const next = await run(() => api.saveSettings(patch));
    if (next) {
      setSettings(next);
      await refresh();
      onChanged();
    }
  };
  const changed = useCallback(() => {
    void refresh();
    onChanged();
  }, [refresh, onChanged]);

  if (!settings) return null;
  const installed = new Set(runtime?.models.map((m) => m.name.replace(/:latest$/, "")) ?? []);

  return (
    <Modal title={t("settings")} onClose={onClose}>
      <div className="flex flex-col gap-6 text-sm">
        <p className="text-muted">{t("privacy")}</p>

        <section className="flex flex-col gap-2">
          <Label>{t("runtime")}</Label>
          <div className="flex flex-wrap gap-4">
            {RUNTIMES.map(({ kind, label }) => (
              <label key={kind} className="flex items-center gap-1.5">
                <input type="radio" name="runtime" checked={settings.runtime === kind} onChange={() => void save({ runtime: kind })} />
                {t(label)}
              </label>
            ))}
          </div>
          {builtin ? (
            <p className="text-xs text-muted">
              {t("builtinHint")}
              {runtime?.version ? ` (llama.cpp ${runtime.version})` : ""}
            </p>
          ) : (
            <>
              <label className="flex flex-col gap-1">
                <span>{t("serverUrl")}</span>
                <input
                  key={settings.runtime}
                  defaultValue={settings.runtime === "ollama" ? settings.ollama_url : settings.openai_url}
                  onBlur={(e) => {
                    const value = e.target.value.trim();
                    const field = settings.runtime === "ollama" ? "ollama_url" : "openai_url";
                    if (value && value !== settings[field]) void save({ [field]: value });
                  }}
                  className="border-hair border-ink bg-white px-2 py-1.5 font-mono"
                />
              </label>
              <div className="flex flex-wrap items-center gap-3">
                <span className={runtime?.reachable ? "text-ink" : "text-danger"} data-testid="runtime-state">
                  {runtime?.reachable ? t("reachable", { version: runtime.version ?? "?" }) : t("unreachable")}
                </span>
                <Button variant="ghost" onClick={() => void refresh()}>
                  <RefreshCw size={14} /> {t("refresh")}
                </Button>
                <Button variant="ghost" onClick={() => void openHelp(settings.runtime === "ollama" ? "ollama" : "lmstudio")}>
                  <ExternalLink size={14} /> {settings.runtime === "ollama" ? t("installOllama") : t("installLmStudio")}
                </Button>
                <Button variant="ghost" onClick={() => void openHelp("models")}>
                  <ExternalLink size={14} /> {t("modelGuide")}
                </Button>
              </div>
            </>
          )}
          {runtime?.error && !runtime.reachable && <p className="text-xs text-danger">{runtime.error.message}</p>}
        </section>

        {builtin ? (
          <BuiltinModelsSection active={settings.model} runtime={runtime} onUse={(id) => save({ model: id })} onChanged={changed} />
        ) : (
          <section className="flex flex-col gap-2">
            <Label>{t("model")}</Label>
            <select
              value={settings.model}
              onChange={(e) => void save({ model: e.target.value })}
              className="border-hair border-ink bg-white px-2 py-1.5"
              aria-label={t("model")}
            >
              <option value="">{t("chooseModel")}</option>
              {settings.model && !runtime?.models.some((m) => m.name === settings.model) && <option value={settings.model}>{settings.model}</option>}
              {runtime?.models.map((m) => (
                <option key={m.name} value={m.name}>
                  {m.name}
                  {m.parameters ? ` · ${m.parameters}` : ""}
                  {m.vision === false ? " · text only" : ""}
                </option>
              ))}
            </select>
            {pulling && (
              <div className="flex items-center gap-3 text-accent">
                <span>{t("downloading", { model: runtime?.pull.model ?? "", progress: percent(runtime?.pull.completed, runtime?.pull.total) || (runtime?.pull.status ?? "") })}</span>
                <Button variant="ghost" onClick={() => void run(() => api.cancelPull()).then(refresh)}>
                  <Square size={14} /> {t("cancel")}
                </Button>
              </div>
            )}
            {runtime?.pull.state === "error" && (
              <p className="text-xs text-danger">{typeof runtime.pull.error === "string" ? runtime.pull.error : runtime.pull.error?.message}</p>
            )}
            <p className="mt-2 font-medium">{t("suggested")}</p>
            <ul className="flex flex-col gap-2" data-testid="catalog">
              {catalog.map((entry) => {
                const isInstalled = installed.has(entry.name.replace(/:latest$/, ""));
                const active = settings.model === entry.name;
                return (
                  <li key={entry.name} className="flex items-start gap-3 border-hair border-line bg-white p-3">
                    <div className="flex-1">
                      <p className="font-semibold">
                        {entry.label} <span className="font-mono text-xs text-muted">{entry.name}</span>
                        {entry.recommended && <span className="ml-2 bg-accent px-1.5 py-0.5 text-[10px] text-white uppercase">{t("recommended")}</span>}
                      </p>
                      <p className="text-xs text-muted">{t("needsRam", { gb: entry.min_ram_gb, size: entry.download_gb })}</p>
                      <p className="mt-1 text-xs">{entry.notes}</p>
                    </div>
                    {active ? (
                      <span className="text-xs font-semibold">{t("inUse")}</span>
                    ) : isInstalled || settings.runtime !== "ollama" ? (
                      <Button onClick={() => void save({ model: entry.name })}>{t("use")}</Button>
                    ) : (
                      <Button
                        disabled={pulling || !runtime?.reachable}
                        onClick={async () => {
                          await save({ model: entry.name });
                          await run(() => api.pull(entry.name));
                          await refresh();
                        }}
                      >
                        <Download size={14} /> {t("download")}
                      </Button>
                    )}
                  </li>
                );
              })}
            </ul>
          </section>
        )}

        <section className="grid gap-3 sm:grid-cols-3">
          {!builtin && (
            <>
              <label className="flex flex-col gap-1">
                <span>{t("extractionMode")}</span>
                <select value={settings.extraction_mode} onChange={(e) => void save({ extraction_mode: e.target.value as Settings["extraction_mode"] })} className="border-hair border-ink bg-white px-2 py-1.5">
                  {(["auto", "structured", "ocr"] as const).map((mode) => (
                    <option key={mode} value={mode}>
                      {t(`mode_${mode}`)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex flex-col gap-1">
                <span>{t("maxImageSide")}</span>
                <input type="number" min={512} max={4096} step={64} defaultValue={settings.max_image_side} onBlur={(e) => Number(e.target.value) !== settings.max_image_side && void save({ max_image_side: Number(e.target.value) })} className="border-hair border-ink bg-white px-2 py-1.5" />
              </label>
            </>
          )}
          <label className="flex flex-col gap-1">
            <span>{t("timeout")}</span>
            <input type="number" min={30} max={3600} step={30} defaultValue={settings.request_timeout} onBlur={(e) => Number(e.target.value) !== settings.request_timeout && void save({ request_timeout: Number(e.target.value) })} className="border-hair border-ink bg-white px-2 py-1.5" />
          </label>
        </section>

        <section className="flex items-center gap-3">
          <Label>{t("language")}</Label>
          {(["de", "en"] as Language[]).map((lang) => (
            <Button
              key={lang}
              variant={language === lang ? "primary" : "secondary"}
              onClick={() => {
                setLanguage(lang);
                void save({ language: lang });
              }}
            >
              {lang.toUpperCase()}
            </Button>
          ))}
        </section>
      </div>
    </Modal>
  );
}
