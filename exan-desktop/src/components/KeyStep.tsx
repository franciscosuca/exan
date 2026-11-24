import { useEffect, useState } from "react";
import { Plus, ScanText, Trash2 } from "lucide-react";
import { useI18n } from "../lib/i18n";
import { useApp } from "../lib/store";
import type { KeyItem } from "../lib/types";
import { Dropzone } from "./Dropzone";
import { Button, Label, PageImage, StatusBadge, formatNumber } from "./ui";

function sameItems(a: KeyItem[], b: KeyItem[]): boolean {
  return a.length === b.length && a.every((item, i) => item.question === b[i].question && item.answer === b[i].answer && item.points === b[i].points);
}

export function KeyStep({ onPhone }: { onPhone: () => void }) {
  const { t, language } = useI18n();
  const { api, session, act } = useApp();
  const key = session?.key;
  const [rows, setRows] = useState<KeyItem[]>([]);
  const [dirty, setDirty] = useState(false);
  const [text, setText] = useState("");
  const [showText, setShowText] = useState(false);

  useEffect(() => {
    if (key && !dirty) setRows(key.items.map((item) => ({ ...item })));
  }, [key, dirty]);

  if (!key) return null;
  const busy = key.status === "processing" || key.status === "queued";

  const edit = (index: number, patch: Partial<KeyItem>) => {
    setRows((current) => current.map((row, i) => (i === index ? { ...row, ...patch } : row)));
    setDirty(true);
  };

  const save = async () => {
    const items = rows.filter((row) => row.question.trim());
    if (await act(() => api.saveKeyItems(items))) setDirty(false);
  };

  const fromText = async (mode: "replace" | "append") => {
    if (await act(() => api.keyFromText(text, mode))) {
      setDirty(false);
      setText("");
      setShowText(false);
    }
  };

  return (
    <div className="grid gap-8 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
      <section className="flex flex-col gap-4">
        <Label>{t("stepKey")}</Label>
        <p className="text-sm text-muted">{t("keyIntro")}</p>
        <Dropzone onFiles={async (files) => void (await act(() => api.addKeyPages(files)))} onPhone={onPhone} />
        {key.pages.length > 0 && (
          <div className="grid grid-cols-3 gap-3">
            {key.pages.map((page) => (
              <figure key={page.id} className="group relative border-hair border-line bg-white">
                <PageImage pageId={page.id} size="thumb" alt={page.name} className="aspect-[3/4] w-full object-contain" />
                <figcaption className="truncate px-2 py-1 text-xs text-muted">{page.name}</figcaption>
                <button
                  type="button"
                  aria-label={`${t("remove")} ${page.name}`}
                  className="absolute top-1 right-1 bg-white p-1 text-danger opacity-0 group-hover:opacity-100 focus:opacity-100"
                  onClick={() => void act(() => api.deleteKeyPage(page.id))}
                >
                  <Trash2 size={14} />
                </button>
              </figure>
            ))}
          </div>
        )}
        <div className="flex flex-wrap items-center gap-3">
          <Button variant="primary" disabled={key.pages.length === 0 || busy} onClick={() => void act(() => api.extractKey())}>
            <ScanText size={16} /> {key.items.length > 0 ? t("readAgain") : t("readWithModel")}
          </Button>
          <StatusBadge status={key.status} progress={key.progress} />
        </div>
        {key.error && <p className="text-sm text-danger">{key.error.message}</p>}
        <div>
          <Button variant="ghost" className="px-0" onClick={() => setShowText((value) => !value)}>
            {t("pasteText")}
          </Button>
          {showText && (
            <div className="mt-2 flex flex-col gap-2">
              <p className="text-xs text-muted">{t("pasteHint")}</p>
              <textarea
                value={text}
                onChange={(event) => setText(event.target.value)}
                rows={6}
                aria-label={t("pasteText")}
                className="border-hair border-ink bg-white p-2 font-mono text-sm"
                placeholder={"1. B\n2. C\n3: Berlin"}
              />
              <div className="flex gap-2">
                <Button variant="primary" disabled={!text.trim()} onClick={() => void fromText("replace")}>
                  {t("replace")}
                </Button>
                <Button disabled={!text.trim()} onClick={() => void fromText("append")}>
                  {t("append")}
                </Button>
              </div>
            </div>
          )}
        </div>
      </section>

      <section className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <Label>
            {t("answer")} · {t("maxScore", { points: formatNumber(key.max_score, language, 2) })}
          </Label>
          <div className="flex gap-2">
            {dirty && (
              <Button variant="ghost" onClick={() => setDirty(false)}>
                {t("cancel")}
              </Button>
            )}
            <Button variant="primary" disabled={!dirty || sameItems(rows, key.items)} onClick={() => void save()}>
              {t("save")}
            </Button>
          </div>
        </div>
        {key.duplicates.length > 0 && <p className="text-sm text-danger">{t("duplicates", { list: key.duplicates.join(", ") })}</p>}
        {rows.length === 0 ? (
          <p className="border-hair border-line bg-white p-6 text-sm text-muted">{t("keyEmpty")}</p>
        ) : (
          <table className="w-full border-collapse bg-white text-sm" data-testid="key-table">
            <thead>
              <tr className="border-b-hair border-ink text-left">
                <th className="w-24 px-2 py-2 font-medium">{t("question")}</th>
                <th className="px-2 py-2 font-medium">{t("answer")}</th>
                <th className="w-24 px-2 py-2 font-medium">{t("points")}</th>
                <th className="w-10" />
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => (
                <tr key={index} className="border-b-hair border-line">
                  <td className="px-1 py-1">
                    <input aria-label={`${t("question")} ${index + 1}`} value={row.question} onChange={(e) => edit(index, { question: e.target.value })} className="w-full px-1 py-1" />
                  </td>
                  <td className="px-1 py-1">
                    <input aria-label={`${t("answer")} ${index + 1}`} value={row.answer} onChange={(e) => edit(index, { answer: e.target.value })} className="w-full px-1 py-1" />
                  </td>
                  <td className="px-1 py-1">
                    <input
                      aria-label={`${t("points")} ${index + 1}`}
                      type="number"
                      min={0}
                      step={0.5}
                      value={row.points}
                      onChange={(e) => edit(index, { points: Math.max(0, Number(e.target.value) || 0) })}
                      className="w-full px-1 py-1"
                    />
                  </td>
                  <td>
                    <button type="button" aria-label={`${t("remove")} ${row.question}`} className="p-1 text-danger" onClick={() => { setRows((current) => current.filter((_, i) => i !== index)); setDirty(true); }}>
                      <Trash2 size={14} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <div>
          <Button
            onClick={() => {
              const next = rows.length + 1;
              setRows((current) => [...current, { question: String(next), answer: "", points: 1 }]);
              setDirty(true);
            }}
          >
            <Plus size={16} /> {t("addRow")}
          </Button>
        </div>
      </section>
    </div>
  );
}
