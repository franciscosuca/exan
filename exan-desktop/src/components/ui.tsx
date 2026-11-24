import { useEffect, useState, type ButtonHTMLAttributes, type ReactNode } from "react";
import { X } from "lucide-react";
import { useI18n } from "../lib/i18n";
import { useApp } from "../lib/store";
import type { JobStatus, Verdict } from "../lib/types";

type Variant = "primary" | "secondary" | "ghost" | "danger";

const variants: Record<Variant, string> = {
  primary: "bg-ink text-white hover:bg-accent disabled:bg-line disabled:text-muted",
  secondary: "border-hair border-ink bg-white text-ink hover:border-accent hover:text-accent disabled:text-muted",
  ghost: "text-ink hover:text-accent disabled:text-muted",
  danger: "text-danger hover:underline disabled:text-muted",
};

export function Button({
  variant = "secondary",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      type="button"
      className={`inline-flex items-center gap-2 px-3 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed ${variants[variant]} ${className}`}
      {...props}
    />
  );
}

export function Label({ children }: { children: ReactNode }) {
  return <span className="text-[11px] font-semibold tracking-[0.08em] text-muted uppercase">{children}</span>;
}

const statusColors: Record<JobStatus, string> = {
  idle: "text-muted",
  queued: "text-muted",
  processing: "text-accent",
  done: "text-ink",
  error: "text-danger",
};

export function StatusBadge({ status, progress }: { status: JobStatus; progress?: { done: number; total: number } }) {
  const { t } = useI18n();
  const suffix = status === "processing" && progress && progress.total > 1 ? ` ${progress.done}/${progress.total}` : "";
  return (
    <span className={`text-xs font-medium ${statusColors[status]}`} data-status={status}>
      {status === "processing" && <span className="mr-1 inline-block h-2 w-2 animate-pulse bg-accent" />}
      {t(`status_${status}`)}
      {suffix}
    </span>
  );
}

const verdictColors: Record<Verdict, string> = {
  correct: "bg-ink text-white",
  incorrect: "bg-danger text-white",
  review: "bg-accent text-white",
  missing: "border-hair border-line text-muted",
};

export function VerdictBadge({ verdict }: { verdict: Verdict }) {
  const { t } = useI18n();
  return <span className={`px-2 py-0.5 text-xs font-medium ${verdictColors[verdict]}`}>{t(`verdict_${verdict}`)}</span>;
}

export function Modal({ title, onClose, children, wide = false }: { title: string; onClose: () => void; children: ReactNode; wide?: boolean }) {
  const { t } = useI18n();
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  return (
    <div className="fixed inset-0 z-40 flex items-start justify-center overflow-y-auto bg-black/40 p-6" onMouseDown={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={`w-full border-hair border-ink bg-surface ${wide ? "max-w-6xl" : "max-w-2xl"}`}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b-hair border-ink px-5 py-3">
          <h2 className="text-base font-semibold">{title}</h2>
          <Button variant="ghost" onClick={onClose} aria-label={t("close")}>
            <X size={18} />
          </Button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}

export function PageImage({ pageId, size, alt, className = "" }: { pageId: string; size: "thumb" | "full"; alt: string; className?: string }) {
  const { image } = useApp();
  const [src, setSrc] = useState<string | null>(null);
  useEffect(() => {
    let active = true;
    image(pageId, size).then(
      (url) => active && setSrc(url),
      () => active && setSrc(null),
    );
    return () => {
      active = false;
    };
  }, [image, pageId, size]);
  return src ? (
    <img src={src} alt={alt} className={className} draggable={false} />
  ) : (
    <div className={`bg-line/40 ${className}`} aria-label={alt} />
  );
}

export function NoticeBar() {
  const { notice, dismiss } = useApp();
  const { t } = useI18n();
  if (!notice) return null;
  return (
    <div
      role={notice.kind === "error" ? "alert" : "status"}
      className={`flex items-start justify-between gap-4 border-b-hair px-6 py-3 text-sm ${notice.kind === "error" ? "border-danger bg-danger/5 text-danger" : "border-ink bg-white"}`}
    >
      <div>
        <p className="font-medium">{notice.text}</p>
        {notice.details?.map((line) => (
          <p key={line} className="mt-0.5 text-xs">
            {line}
          </p>
        ))}
      </div>
      <Button variant="ghost" onClick={dismiss} aria-label={t("close")}>
        <X size={16} />
      </Button>
    </div>
  );
}

export function formatNumber(value: number | null | undefined, language: string, digits = 1): string {
  if (value === null || value === undefined) return "–";
  return new Intl.NumberFormat(language === "de" ? "de-DE" : "en-US", { maximumFractionDigits: digits }).format(value);
}
