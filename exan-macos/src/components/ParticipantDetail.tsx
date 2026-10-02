import { useState } from "react";
import { Check, RotateCcw, ScanText, Trash2, X } from "lucide-react";
import { useI18n } from "../lib/i18n";
import { useApp } from "../lib/store";
import type { AnswerView, ParticipantView } from "../lib/types";
import { Dropzone } from "./Dropzone";
import { participantName } from "./ParticipantsStep";
import { Button, Label, Modal, PageImage, StatusBadge, VerdictBadge, formatNumber } from "./ui";

export function ParticipantDetail({ participant, onClose }: { participant: ParticipantView; onClose: () => void }) {
  const { t, language } = useI18n();
  const { api, act } = useApp();
  const [name, setName] = useState(participant.name);
  const [editing, setEditing] = useState<AnswerView[] | null>(null);
  const [page, setPage] = useState(0);
  const current = participant.pages[Math.min(page, participant.pages.length - 1)];
  const result = participant.result;

  const startEditing = () => {
    const given = new Map(participant.answers.map((a) => [a.question, a.answer]));
    const rows = result.questions.map((q) => ({ question: q.question, answer: given.get(q.question) ?? q.given }));
    for (const extra of result.extra) rows.push({ ...extra });
    setEditing(rows);
  };

  return (
    <Modal title={participantName(participant, t)} onClose={onClose} wide>
      <div className="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
        <section className="flex flex-col gap-3">
          {current ? (
            <PageImage pageId={current.id} size="full" alt={current.name} className="max-h-[60vh] w-full border-hair border-line bg-white object-contain" />
          ) : (
            <p className="text-sm text-muted">–</p>
          )}
          {participant.pages.length > 1 && (
            <div className="flex flex-wrap gap-2">
              {participant.pages.map((p, index) => (
                <Button key={p.id} variant={index === page ? "primary" : "secondary"} onClick={() => setPage(index)}>
                  {index + 1}
                </Button>
              ))}
            </div>
          )}
          {current && (
            <Button variant="danger" className="self-start px-0" onClick={() => void act(() => api.deleteParticipantPage(participant.id, current.id))}>
              <Trash2 size={14} /> {t("remove")} {current.name}
            </Button>
          )}
          <Dropzone compact onFiles={async (files) => void (await act(() => api.addParticipantPages(participant.id, files)))} />
        </section>

        <section className="flex flex-col gap-4">
          <div className="flex flex-wrap items-end gap-3">
            <label className="flex flex-1 flex-col gap-1">
              <Label>{t("name")}</Label>
              <input value={name} onChange={(e) => setName(e.target.value)} className="border-hair border-ink bg-white px-2 py-1.5" />
            </label>
            <Button variant="primary" disabled={name === participant.name} onClick={() => void act(() => api.patchParticipant(participant.id, { name }))}>
              {t("save")}
            </Button>
          </div>
          <div className="flex flex-wrap items-center gap-3 text-sm">
            <StatusBadge status={participant.status} progress={participant.progress} />
            <span className="font-semibold">
              {formatNumber(result.score, language, 2)} / {formatNumber(result.max_score, language, 2)}
              {result.percent !== null && ` · ${formatNumber(result.percent, language)} %`}
            </span>
            <Button className="ml-auto" disabled={participant.pages.length === 0} onClick={() => void act(() => api.extractParticipant(participant.id))}>
              <ScanText size={16} /> {t("readAgain")}
            </Button>
            <Button onClick={startEditing}>{t("editAnswers")}</Button>
          </div>
          {participant.error && <p className="text-sm text-danger">{participant.error.message}</p>}

          {editing ? (
            <div className="flex flex-col gap-2">
              {editing.map((row, index) => (
                <label key={index} className="grid grid-cols-[6rem_1fr] items-center gap-2 text-sm">
                  <span className="font-medium">{row.question}</span>
                  <input
                    aria-label={`${t("answer")} ${row.question}`}
                    value={row.answer}
                    onChange={(e) => setEditing((rows) => rows && rows.map((r, i) => (i === index ? { ...r, answer: e.target.value } : r)))}
                    className="border-hair border-ink bg-white px-2 py-1"
                  />
                </label>
              ))}
              <div className="flex gap-2">
                <Button
                  variant="primary"
                  onClick={async () => {
                    if (await act(() => api.patchParticipant(participant.id, { answers: editing }))) setEditing(null);
                  }}
                >
                  {t("save")}
                </Button>
                <Button variant="ghost" onClick={() => setEditing(null)}>
                  {t("cancel")}
                </Button>
              </div>
            </div>
          ) : (
            <table className="w-full border-collapse bg-white text-sm" data-testid="answers-table">
              <thead>
                <tr className="border-b-hair border-ink text-left">
                  <th className="px-2 py-2 font-medium">{t("question")}</th>
                  <th className="px-2 py-2 font-medium">{t("expected")}</th>
                  <th className="px-2 py-2 font-medium">{t("given")}</th>
                  <th className="px-2 py-2 font-medium" />
                  <th className="px-2 py-2 text-right font-medium">{t("points")}</th>
                </tr>
              </thead>
              <tbody>
                {result.questions.map((q) => (
                  <tr key={q.key} className="border-b-hair border-line align-top">
                    <td className="px-2 py-2 font-medium">{q.question}</td>
                    <td className="px-2 py-2">{q.expected}</td>
                    <td className="px-2 py-2">{q.given || "–"}</td>
                    <td className="px-2 py-2">
                      <div className="flex flex-wrap items-center gap-1">
                        <VerdictBadge verdict={q.final} />
                        <button type="button" title={t("markCorrect")} aria-label={`${t("markCorrect")} ${q.question}`} className={`p-1 ${q.override === "correct" ? "text-accent" : "text-muted hover:text-ink"}`} onClick={() => void act(() => api.override(participant.id, q.question, "correct"))}>
                          <Check size={14} />
                        </button>
                        <button type="button" title={t("markIncorrect")} aria-label={`${t("markIncorrect")} ${q.question}`} className={`p-1 ${q.override === "incorrect" ? "text-danger" : "text-muted hover:text-ink"}`} onClick={() => void act(() => api.override(participant.id, q.question, "incorrect"))}>
                          <X size={14} />
                        </button>
                        {q.override && (
                          <button type="button" title={t("resetVerdict")} aria-label={`${t("resetVerdict")} ${q.question}`} className="p-1 text-muted hover:text-ink" onClick={() => void act(() => api.override(participant.id, q.question, null))}>
                            <RotateCcw size={14} />
                          </button>
                        )}
                      </div>
                    </td>
                    <td className="px-2 py-2 text-right">
                      {formatNumber(q.earned, language, 2)} / {formatNumber(q.points, language, 2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {result.extra.length > 0 && !editing && (
            <div className="text-sm">
              <Label>{t("extraAnswers")}</Label>
              <ul className="mt-1">
                {result.extra.map((a) => (
                  <li key={a.question}>
                    {a.question}: {a.answer}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>
      </div>
    </Modal>
  );
}
