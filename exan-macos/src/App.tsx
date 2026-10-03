import { useEffect, useState } from "react";
import { RotateCcw, Settings as SettingsIcon } from "lucide-react";
import { Button, NoticeBar } from "./components/ui";
import { KeyStep } from "./components/KeyStep";
import { ParticipantsStep } from "./components/ParticipantsStep";
import { ResultsStep } from "./components/ResultsStep";
import { SettingsPanel, useRuntime } from "./components/SettingsPanel";
import { PhoneDialog } from "./components/PhoneDialog";
import { confirmAction, restartEngine, watchEngine, type Connection, type EngineStatus } from "./lib/bridge";
import { I18nProvider, useI18n, type Language } from "./lib/i18n";
import { AppProvider, useApp } from "./lib/store";
import type { PhoneTarget } from "./lib/types";

type Step = "key" | "participants" | "results";

function Workspace() {
  const { t, language, setLanguage } = useI18n();
  const { api, session, act } = useApp();
  const [step, setStep] = useState<Step>("key");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [phoneTarget, setPhoneTarget] = useState<PhoneTarget | null>(null);
  const { runtime, refresh } = useRuntime();

  useEffect(() => {
    void api.saveSettings({ language }).catch(() => undefined);
  }, [api, language]);

  const ready = runtime?.reachable && runtime.model_installed;
  const steps: [Step, string, number | null][] = [
    ["key", t("stepKey"), session?.key.items.length ?? null],
    ["participants", t("stepParticipants"), session?.participants.length ?? null],
    ["results", t("stepResults"), session?.stats.graded ?? null],
  ];

  return (
    <div className="flex min-h-screen flex-col bg-surface text-ink">
      <header className="flex items-center gap-6 border-b-hair border-ink bg-white px-6 py-3">
        <div className="flex items-baseline gap-3">
          <span className="text-lg font-bold tracking-tight">EXAN</span>
          <span className="hidden text-xs text-muted md:inline">{t("appTagline")}</span>
        </div>
        <nav className="flex gap-1" aria-label="steps">
          {steps.map(([id, label, count], index) => (
            <button
              key={id}
              type="button"
              onClick={() => setStep(id)}
              aria-current={step === id ? "step" : undefined}
              className={`px-3 py-2 text-sm font-medium ${step === id ? "bg-ink text-white" : "hover:text-accent"}`}
            >
              {index + 1}. {label}
              {count ? <span className="ml-1.5 text-xs opacity-70">{count}</span> : null}
            </button>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-2">
          {(["de", "en"] as Language[]).map((lang) => (
            <button key={lang} type="button" onClick={() => setLanguage(lang)} className={`px-1.5 text-xs font-semibold ${language === lang ? "text-ink underline" : "text-muted"}`}>
              {lang.toUpperCase()}
            </button>
          ))}
          <Button
            variant="ghost"
            onClick={() =>
              void confirmAction(t("newSessionConfirm"), t("delete"), t("cancel")).then(async (confirmed) => {
                if (!confirmed) return;
                await act(() => api.resetSession());
                setStep("key");
              })
            }
          >
            <RotateCcw size={16} /> {t("newSession")}
          </Button>
          <Button variant="ghost" onClick={() => setSettingsOpen(true)} aria-label={t("settings")}>
            <SettingsIcon size={18} /> <span className="hidden lg:inline">{t("settings")}</span>
          </Button>
        </div>
      </header>
      {runtime && !ready && (
        <div className="flex items-center justify-between gap-4 border-b-hair border-accent bg-accent/5 px-6 py-3 text-sm text-accent" data-testid="setup-banner">
          <span>{t("setupNeeded")}</span>
          <Button variant="primary" onClick={() => setSettingsOpen(true)}>
            {t("openSettings")}
          </Button>
        </div>
      )}
      <NoticeBar />
      <main className="mx-auto w-full max-w-7xl flex-1 px-6 py-8">
        {!session ? (
          <p className="text-sm text-muted">{t("engineStarting")}</p>
        ) : step === "key" ? (
          <KeyStep onPhone={() => setPhoneTarget("key")} />
        ) : step === "participants" ? (
          <ParticipantsStep onPhone={() => setPhoneTarget("participants")} />
        ) : (
          <ResultsStep onOpen={() => setStep("participants")} />
        )}
      </main>
      <footer className="border-t-hair border-line px-6 py-2 text-xs text-muted">{t("privacy")}</footer>
      {settingsOpen && (
        <SettingsPanel
          onClose={() => {
            setSettingsOpen(false);
            void refresh();
          }}
          onChanged={() => void refresh()}
        />
      )}
      {phoneTarget && <PhoneDialog target={phoneTarget} onClose={() => setPhoneTarget(null)} />}
    </div>
  );
}

function EngineGate() {
  const { t } = useI18n();
  const [status, setStatus] = useState<EngineStatus>({ state: "starting", port: null, token: null, error: null, restarts: 0 });
  const [connection, setConnection] = useState<Connection | null>(null);

  useEffect(
    () =>
      watchEngine((next, nextConnection) => {
        setStatus(next);
        setConnection((previous) =>
          previous && nextConnection && previous.baseUrl === nextConnection.baseUrl && previous.token === nextConnection.token
            ? previous
            : nextConnection,
        );
      }),
    [],
  );

  if (!connection) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-surface p-8 text-center text-ink">
        <span className="text-2xl font-bold tracking-tight">EXAN</span>
        {status.state === "failed" || status.state === "stopped" ? (
          <>
            <p className="font-medium text-danger">{t("engineFailed")}</p>
            {status.error && <p className="max-w-xl text-xs break-words text-muted">{status.error}</p>}
            <Button variant="primary" onClick={() => void restartEngine()}>
              {t("engineRestart")}
            </Button>
          </>
        ) : (
          <p className="text-sm text-muted" role="status">
            {t("engineStarting")}
          </p>
        )}
      </div>
    );
  }
  return (
    <AppProvider key={connection.baseUrl + connection.token} connection={connection}>
      <Workspace />
    </AppProvider>
  );
}

export default function App() {
  return (
    <I18nProvider>
      <EngineGate />
    </I18nProvider>
  );
}
