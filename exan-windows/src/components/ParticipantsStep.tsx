import { useState } from "react";
import { RotateCw, ScanText, Square, Trash2 } from "lucide-react";
import { useI18n } from "../lib/i18n";
import { useApp } from "../lib/store";
import type { Grouping, ParticipantView } from "../lib/types";
import { Dropzone } from "./Dropzone";
import { ParticipantDetail } from "./ParticipantDetail";
import { Button, Label, PageImage, StatusBadge, formatNumber } from "./ui";

export function participantName(participant: ParticipantView, t: ReturnType<typeof useI18n>["t"]): string {
  return participant.name.trim() || t("participant", { n: participant.number });
}

export function ParticipantsStep({ onPhone }: { onPhone: () => void }) {
  const { t, language } = useI18n();
  const { api, session, act } = useApp();
  const [grouping, setGrouping] = useState<Grouping>("file");
  const [openId, setOpenId] = useState<string | null>(null);
  if (!session) return null;
  const participants = session.participants;
  const open = participants.find((p) => p.id === openId) ?? null;
  const busy = session.jobs.running || session.jobs.queued > 0;
  const pending = participants.some((p) => p.pages.length > 0 && (p.status === "idle" || p.status === "error"));

  return (
    <div className="flex flex-col gap-6">
      {session.key.items.length === 0 && <p className="border-hair border-accent bg-white p-3 text-sm text-accent">{t("needKey")}</p>}
      <Dropzone onFiles={async (files) => void (await act(() => api.addParticipants(files, grouping)))} onPhone={onPhone}>
        <fieldset className="flex flex-wrap justify-center gap-4 text-sm">
          <legend className="sr-only">{t("grouping")}</legend>
          {(["file", "page", "single"] as const).map((value) => (
            <label key={value} className="flex items-center gap-1.5">
              <input type="radio" name="grouping" value={value} checked={grouping === value} onChange={() => setGrouping(value)} />
              {t(`grouping_${value}`)}
            </label>
          ))}
        </fieldset>
      </Dropzone>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <Label>
          {t("stepParticipants")} · {participants.length}
        </Label>
        <div className="flex gap-2">
          {busy && (
            <Button variant="ghost" onClick={() => void act(() => api.cancelJobs())}>
              <Square size={14} /> {t("stopJobs")}
            </Button>
          )}
          <Button variant="primary" disabled={!pending} onClick={() => void act(() => api.extractParticipants("pending"))}>
            <ScanText size={16} /> {t("readPending")}
          </Button>
          <Button disabled={participants.length === 0} onClick={() => void act(() => api.extractParticipants("all"))}>
            <RotateCw size={16} /> {t("readAll")}
          </Button>
        </div>
      </div>

      {participants.length === 0 ? (
        <p className="border-hair border-line bg-white p-6 text-sm text-muted">{t("participantsEmpty")}</p>
      ) : (
        <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3" data-testid="participants">
          {participants.map((participant) => (
            <li key={participant.id} className="flex gap-3 border-hair border-line bg-white p-3">
              {participant.pages[0] ? (
                <PageImage pageId={participant.pages[0].id} size="thumb" alt={participantName(participant, t)} className="h-24 w-18 shrink-0 object-cover" />
              ) : (
                <div className="h-24 w-18 shrink-0 bg-line/40" />
              )}
              <div className="flex min-w-0 flex-1 flex-col gap-1">
                <button type="button" className="truncate text-left font-semibold hover:text-accent" onClick={() => setOpenId(participant.id)}>
                  {participantName(participant, t)}
                </button>
                <StatusBadge status={participant.status} progress={participant.progress} />
                {participant.graded && (
                  <p className="text-sm">
                    {formatNumber(participant.result.score, language, 2)} / {formatNumber(participant.result.max_score, language, 2)} ·{" "}
                    {participant.result.percent === null ? "–" : `${formatNumber(participant.result.percent, language)} %`}
                    {participant.result.counts.review > 0 && (
                      <span className="ml-2 text-accent">
                        {participant.result.counts.review} × {t("review")}
                      </span>
                    )}
                  </p>
                )}
                {participant.error && <p className="truncate text-xs text-danger" title={participant.error.message}>{participant.error.message}</p>}
                <div className="mt-auto flex gap-2">
                  <Button variant="ghost" className="px-0" onClick={() => setOpenId(participant.id)}>
                    {t("details")}
                  </Button>
                  <Button
                    variant="danger"
                    className="ml-auto px-1"
                    aria-label={`${t("delete")} ${participantName(participant, t)}`}
                    onClick={() => window.confirm(t("deleteConfirm")) && void act(() => api.deleteParticipant(participant.id))}
                  >
                    <Trash2 size={14} />
                  </Button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
      {open && <ParticipantDetail participant={open} onClose={() => setOpenId(null)} />}
    </div>
  );
}
