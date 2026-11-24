import { useEffect, useState } from "react";
import { useI18n } from "../lib/i18n";
import { useApp } from "../lib/store";
import type { PhoneTarget, PhoneView } from "../lib/types";
import { Button, Label, Modal } from "./ui";

export function PhoneDialog({ target, onClose }: { target: PhoneTarget; onClose: () => void }) {
  const { t } = useI18n();
  const { api, run, session } = useApp();
  const [phone, setPhone] = useState<PhoneView | null>(null);
  const uploads = session?.phone.uploads ?? 0;

  useEffect(() => {
    void run(() => api.startPhone(target)).then((view) => view && setPhone(view));
  }, [api, run, target]);

  useEffect(() => {
    if (!phone?.active) return;
    void api.phone().then(setPhone, () => undefined);
  }, [api, uploads, phone?.active]);

  const switchTarget = async (next: PhoneTarget) => {
    const view = await run(() => api.phoneTarget(next));
    if (view) setPhone(view);
  };

  const stop = async () => {
    await run(() => api.stopPhone());
    onClose();
  };

  return (
    <Modal title={t("phoneTitle")} onClose={onClose}>
      <div className="flex flex-col gap-4 text-sm">
        <p>{t("phoneIntro")}</p>
        {phone && (
          <>
            <div className="flex items-center gap-3">
              <Label>{t("phoneTarget")}</Label>
              {(["key", "participants"] as const).map((value) => (
                <Button key={value} variant={phone.target === value ? "primary" : "secondary"} onClick={() => void switchTarget(value)}>
                  {value === "key" ? t("stepKey") : t("stepParticipants")}
                </Button>
              ))}
            </div>
            {phone.urls.length === 0 ? (
              <p className="text-danger">{t("phoneNoNetwork")}</p>
            ) : (
              <div className="flex flex-wrap gap-6" data-testid="phone-qr">
                {phone.urls.slice(0, 2).map((entry) => (
                  <figure key={entry.url} className="flex flex-col items-center gap-2">
                    <img
                      src={`data:image/svg+xml;charset=utf-8,${encodeURIComponent(entry.qr)}`}
                      alt={entry.url}
                      className="h-56 w-56 border-hair border-ink bg-white p-2"
                    />
                    <figcaption className="font-mono text-xs break-all">{entry.url}</figcaption>
                  </figure>
                ))}
              </div>
            )}
            <p className="font-medium">{t("phoneUploads", { n: phone.uploads })}</p>
            <p className="text-xs text-muted">{t("phoneFirewall")}</p>
          </>
        )}
        <div className="flex justify-end gap-2">
          <Button variant="danger" onClick={() => void stop()}>
            {t("phoneStop")}
          </Button>
          <Button variant="primary" onClick={onClose}>
            {t("close")}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
