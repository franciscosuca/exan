import { Download } from "lucide-react";
import { saveTextFile } from "../lib/bridge";
import { useI18n } from "../lib/i18n";
import { useApp } from "../lib/store";
import { participantName } from "./ParticipantsStep";
import { Button, Label, formatNumber } from "./ui";

export function ResultsStep({ onOpen }: { onOpen: () => void }) {
  const { t, language } = useI18n();
  const { api, session, run, notify } = useApp();
  if (!session) return null;
  const { stats } = session;
  const graded = session.participants.filter((p) => p.graded);

  const exportCsv = async (kind: "summary" | "detail") => {
    const saved = await run(async () => {
      const csv = await api.exportCsv(kind, language);
      const date = new Date().toISOString().slice(0, 10);
      return saveTextFile(`exan-${kind === "summary" ? (language === "de" ? "uebersicht" : "summary") : (language === "de" ? "antworten" : "answers")}-${date}.csv`, csv);
    });
    if (saved) notify(t("exported"));
  };

  const tiles: [string, string][] = [
    [t("graded"), String(stats.graded)],
    [t("average"), stats.average === null ? "–" : `${formatNumber(stats.average, language)} %`],
    [t("best"), stats.best === null ? "–" : `${formatNumber(stats.best, language)} %`],
    [t("worst"), stats.worst === null ? "–" : `${formatNumber(stats.worst, language)} %`],
    [t("pendingReview"), String(stats.pending_review)],
  ];

  return (
    <div className="flex flex-col gap-8">
      <div className="grid grid-cols-2 gap-px border-hair border-ink bg-ink sm:grid-cols-5" data-testid="stats">
        {tiles.map(([label, value]) => (
          <div key={label} className="bg-white p-4">
            <Label>{label}</Label>
            <p className="mt-1 text-2xl font-semibold">{value}</p>
          </div>
        ))}
      </div>

      <div className="flex flex-wrap gap-2">
        <Button variant="primary" disabled={session.participants.length === 0} onClick={() => void exportCsv("summary")}>
          <Download size={16} /> {t("exportSummary")}
        </Button>
        <Button disabled={session.participants.length === 0} onClick={() => void exportCsv("detail")}>
          <Download size={16} /> {t("exportDetail")}
        </Button>
      </div>

      <section>
        <Label>{t("stepParticipants")}</Label>
        <table className="mt-2 w-full border-collapse bg-white text-sm" data-testid="results-table">
          <thead>
            <tr className="border-b-hair border-ink text-left">
              <th className="px-2 py-2 font-medium">{t("name")}</th>
              <th className="px-2 py-2 text-right font-medium">{t("score")}</th>
              <th className="px-2 py-2 text-right font-medium">{t("percent")}</th>
              <th className="px-2 py-2 text-right font-medium">{t("review")}</th>
            </tr>
          </thead>
          <tbody>
            {graded.map((p) => (
              <tr key={p.id} className="border-b-hair border-line">
                <td className="px-2 py-2">
                  <button type="button" className="hover:text-accent" onClick={onOpen}>
                    {participantName(p, t)}
                  </button>
                </td>
                <td className="px-2 py-2 text-right">
                  {formatNumber(p.result.score, language, 2)} / {formatNumber(p.result.max_score, language, 2)}
                </td>
                <td className="px-2 py-2 text-right">{p.result.percent === null ? "–" : `${formatNumber(p.result.percent, language)} %`}</td>
                <td className={`px-2 py-2 text-right ${p.result.counts.review > 0 ? "text-accent" : ""}`}>{p.result.counts.review}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section>
        <Label>{t("perQuestion")}</Label>
        <table className="mt-2 w-full border-collapse bg-white text-sm">
          <thead>
            <tr className="border-b-hair border-ink text-left">
              <th className="px-2 py-2 font-medium">{t("question")}</th>
              <th className="px-2 py-2 text-right font-medium">{t("verdict_correct")}</th>
              <th className="px-2 py-2 text-right font-medium">{t("verdict_review")}</th>
              <th className="px-2 py-2 text-right font-medium">{t("verdict_missing")}</th>
              <th className="px-2 py-2 text-right font-medium">{t("rate")}</th>
            </tr>
          </thead>
          <tbody>
            {stats.questions.map((q) => (
              <tr key={q.key} className="border-b-hair border-line">
                <td className="px-2 py-2 font-medium">{q.question}</td>
                <td className="px-2 py-2 text-right">{q.correct}</td>
                <td className="px-2 py-2 text-right">{q.review}</td>
                <td className="px-2 py-2 text-right">{q.missing}</td>
                <td className="px-2 py-2 text-right">{q.rate === null ? "–" : `${formatNumber(q.rate, language)} %`}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
