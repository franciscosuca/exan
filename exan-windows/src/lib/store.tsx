import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Api, ApiError } from "./api";
import type { Connection } from "./bridge";
import { useI18n } from "./i18n";
import type { SessionView, Updated, UploadError } from "./types";

interface AppContextValue {
  api: Api;
  session: SessionView | null;
  apply: (updated: Updated | SessionView) => void;
  run: <T>(action: () => Promise<T>) => Promise<T | undefined>;
  act: (action: () => Promise<Updated>) => Promise<Updated | undefined>;
  notify: (message: string) => void;
  notice: { kind: "info" | "error"; text: string; details?: string[] } | null;
  dismiss: () => void;
  image: (pageId: string, size: "thumb" | "full") => Promise<string>;
}

const AppContext = createContext<AppContextValue | null>(null);

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

function isUpdated(value: Updated | SessionView): value is Updated {
  return "session" in value;
}

export function AppProvider({ connection, children }: { connection: Connection; children: ReactNode }) {
  const { t } = useI18n();
  const api = useMemo(() => new Api(connection), [connection]);
  const [session, setSession] = useState<SessionView | null>(null);
  const [notice, setNotice] = useState<AppContextValue["notice"]>(null);
  const images = useRef(new Map<string, Promise<string>>());

  const accept = useCallback((next: SessionView) => {
    setSession((previous) => (!previous || next.version >= previous.version ? next : previous));
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void (async () => {
      let version: number | undefined;
      while (!controller.signal.aborted) {
        try {
          const next = await api.session(version, version === undefined ? 0 : 25, controller.signal);
          version = next.version;
          accept(next);
        } catch {
          if (controller.signal.aborted) return;
          await sleep(1500);
        }
      }
    })();
    return () => controller.abort();
  }, [api, accept]);

  const apply = useCallback(
    (updated: Updated | SessionView) => {
      if (!isUpdated(updated)) {
        accept(updated);
        return;
      }
      accept(updated.session);
      const errors: UploadError[] = updated.errors ?? [];
      if (errors.length > 0) {
        setNotice({
          kind: "error",
          text: t("uploadErrors"),
          details: errors.map((error) => `${error.file}: ${error.message}`),
        });
      }
    },
    [accept, t],
  );

  const run = useCallback(
    async <T,>(action: () => Promise<T>): Promise<T | undefined> => {
      try {
        return await action();
      } catch (error) {
        const text = error instanceof ApiError || error instanceof Error ? error.message : String(error);
        setNotice({ kind: "error", text: t("errorTitle"), details: [text] });
        return undefined;
      }
    },
    [t],
  );

  const act = useCallback(
    async (action: () => Promise<Updated>) => {
      const result = await run(action);
      if (result) apply(result);
      return result;
    },
    [run, apply],
  );

  const image = useCallback(
    (pageId: string, size: "thumb" | "full") => {
      const cacheKey = `${pageId}:${size}`;
      let entry = images.current.get(cacheKey);
      if (!entry) {
        entry = api.image(pageId, size).then((blob) => URL.createObjectURL(blob));
        entry.catch(() => images.current.delete(cacheKey));
        images.current.set(cacheKey, entry);
      }
      return entry;
    },
    [api],
  );

  const value = useMemo<AppContextValue>(
    () => ({
      api,
      session,
      apply,
      run,
      act,
      notify: (text: string) => setNotice({ kind: "info", text }),
      notice,
      dismiss: () => setNotice(null),
      image,
    }),
    [api, session, apply, run, act, notice, image],
  );
  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp(): AppContextValue {
  const context = useContext(AppContext);
  if (!context) throw new Error("useApp must be used inside AppProvider");
  return context;
}
