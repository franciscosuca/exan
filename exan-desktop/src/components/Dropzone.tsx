import { useRef, useState, type DragEvent, type ReactNode } from "react";
import { Smartphone, Upload } from "lucide-react";
import { useI18n } from "../lib/i18n";
import { Button } from "./ui";

export const ACCEPTED_FILES = ".jpg,.jpeg,.png,.webp,.heic,.heif,.pdf,.tif,.tiff,.bmp,image/*,application/pdf";

interface DropzoneProps {
  onFiles: (files: File[]) => Promise<void> | void;
  onPhone?: () => void;
  disabled?: boolean;
  children?: ReactNode;
  compact?: boolean;
}

export function Dropzone({ onFiles, onPhone, disabled = false, children, compact = false }: DropzoneProps) {
  const { t } = useI18n();
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);
  const [busy, setBusy] = useState(false);

  const deliver = async (list: FileList | null) => {
    const files = list ? Array.from(list) : [];
    if (files.length === 0 || disabled) return;
    setBusy(true);
    try {
      await onFiles(files);
    } finally {
      setBusy(false);
      if (input.current) input.current.value = "";
    }
  };

  const onDrop = (event: DragEvent) => {
    event.preventDefault();
    setOver(false);
    void deliver(event.dataTransfer.files);
  };

  return (
    <div
      onDragOver={(event) => {
        event.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={onDrop}
      data-testid="dropzone"
      className={`border-hair border-dashed ${over ? "border-accent bg-accent/5" : "border-ink bg-white"} ${compact ? "p-4" : "p-8"} flex flex-col items-center gap-3 text-center`}
    >
      <Upload size={compact ? 18 : 24} className="text-muted" />
      <p className="text-sm">
        {busy ? (
          t("uploading")
        ) : (
          <>
            {t("dropHere")}{" "}
            <button
              type="button"
              className="font-semibold text-accent underline"
              onClick={() => input.current?.click()}
              disabled={disabled || busy}
            >
              {t("choose")}
            </button>
          </>
        )}
      </p>
      {!compact && <p className="text-xs text-muted">{t("formats")}</p>}
      {children}
      {onPhone && (
        <Button onClick={onPhone} disabled={disabled}>
          <Smartphone size={16} /> {t("fromPhone")}
        </Button>
      )}
      <input
        ref={input}
        type="file"
        multiple
        accept={ACCEPTED_FILES}
        className="hidden"
        data-testid="file-input"
        onChange={(event) => void deliver(event.target.files)}
      />
    </div>
  );
}
