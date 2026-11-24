import { useCallback, useState } from "react";
import { useI18n } from "../lib/i18n";
import { useApp } from "../lib/store";
import type { PullView, RuntimeView } from "../lib/types";
import { MODEL_SOURCE, ModelDetails, PullProgress, formatBytes, pullError, useBuiltinModels, usePull } from "./models";
import { Button } from "./ui";

/**
 * First start (and whenever the chosen model is missing): pick a built-in model and agree to download it.
 * Installers stay small because no model is bundled; nothing is downloaded without this consent.
 */
export function SetupWizard({ runtime, onReady, onAdvanced }: { runtime: RuntimeView; onReady: () => Promise<void> | void; onAdvanced: () => void }) {
  const { t, language } = useI18n();
  const { api, run } = useApp();
  const { models, reload } = useBuiltinModels();
  const [picked, setPicked] = useState(""); // the user's own choice; until then the default below
  const [consent, setConsent] = useState(false);

  const finished = useCallback(
    (pull: PullView) => {
      void reload().then(() => (pull.state === "done" ? onReady() : undefined));
    },
    [reload, onReady],
  );
  const { pull, setPull, running } = usePull(runtime.pull, finished);

  if (!models) return null;
  // Preselect the model chosen earlier (for example in the Windows installer), else the recommended one.
  const preferred = models.find((m) => m.id === runtime.model) ?? models.find((m) => m.recommended) ?? models[0];
  const selected = picked || preferred?.id || "";
  const choice = models.find((m) => m.id === selected);
  const error = pullError(pull);

  const start = async () => {
    if (!choice) return;
    if (!(await run(() => api.saveSettings({ runtime: "builtin", model: choice.id })))) return;
    if (choice.installed) {
      await onReady();
      return;
    }
    const started = await run(() => api.pull(choice.id));
    if (started) setPull(started);
  };

  return (
    <section className="mx-auto flex max-w-3xl flex-col gap-6" data-testid="setup">
      <div className="flex flex-col gap-2">
        <h1 className="text-2xl font-bold tracking-tight">{t("setupTitle")}</h1>
        <p className="text-sm text-muted">{t("setupIntro")}</p>
      </div>

      <fieldset className="flex flex-col gap-2" disabled={running}>
        <legend className="sr-only">{t("setupTitle")}</legend>
        {models.map((model) => (
          <label
            key={model.id}
            className={`flex cursor-pointer gap-3 border-hair bg-white p-4 ${selected === model.id ? "border-ink" : "border-line"}`}
          >
            <input type="radio" name="model" value={model.id} checked={selected === model.id} onChange={() => setPicked(model.id)} className="mt-1" />
            <div className="flex-1">
              <p className="font-semibold">
                {model.label} <span className="text-xs font-normal text-muted">{model.vendor}</span>
                {model.recommended && <span className="ml-2 bg-accent px-1.5 py-0.5 text-[10px] text-white uppercase">{t("recommended")}</span>}
                {model.installed && <span className="ml-2 text-xs text-accent">{t("modelInstalled")}</span>}
              </p>
              <ModelDetails model={model} />
            </div>
          </label>
        ))}
      </fieldset>

      {runtime.error && <p className="text-sm text-danger">{runtime.error.message}</p>}

      {running && pull ? (
        <PullProgress pull={pull} label={models.find((m) => m.id === pull.model)?.label ?? pull.model ?? ""} size={models.find((m) => m.id === pull.model)?.download_bytes} onCancel={() => void run(() => api.cancelPull()).then((next) => next && setPull(next))} />
      ) : (
        <div className="flex flex-col gap-4">
          {choice && !choice.installed && (
            <>
              {choice.downloaded_bytes > 0 && (
                <p className="text-sm text-muted">
                  {t("setupResume", { done: formatBytes(choice.downloaded_bytes, language), total: formatBytes(choice.download_bytes, language) })}
                </p>
              )}
              <label className="flex items-start gap-2 text-sm">
                <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} className="mt-0.5" />
                <span>{t("setupConsent", { size: formatBytes(choice.download_bytes, language), source: MODEL_SOURCE })}</span>
              </label>
            </>
          )}
          {pull?.state === "cancelled" && <p className="text-sm text-muted">{t("setupCancelled")}</p>}
          {error && <p className="text-sm text-danger">{error}</p>}
          <div className="flex flex-wrap items-center gap-3">
            <Button variant="primary" disabled={!choice || (!choice.installed && !consent)} onClick={() => void start()}>
              {choice?.installed ? t("setupUseInstalled") : t("setupDownload")}
            </Button>
            <Button variant="ghost" onClick={onAdvanced}>
              {t("setupAdvanced")}
            </Button>
          </div>
        </div>
      )}
    </section>
  );
}
