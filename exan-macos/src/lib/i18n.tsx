import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

export type Language = "de" | "en";
export const LANGUAGE_STORAGE_KEY = "exan_language";

const de = {
  appTagline: "Prüfungen lokal korrigieren",
  stepKey: "Lösungsschlüssel",
  stepParticipants: "Teilnehmende",
  stepResults: "Ergebnisse",
  settings: "Einstellungen",
  newSession: "Neue Korrektur",
  newSessionConfirm: "Alle Fotos, Antworten und Ergebnisse dieser Korrektur löschen?",
  engineStarting: "Exan startet …",
  engineFailed: "Die lokale Engine läuft nicht.",
  engineRestart: "Neu starten",
  setupNeeded: "Richte zuerst ein lokales Modell ein, damit Exan Fotos lesen kann.",
  openSettings: "Einstellungen öffnen",
  dropHere: "Fotos oder PDFs hierher ziehen oder",
  choose: "Dateien auswählen",
  fromPhone: "Mit dem Handy fotografieren",
  formats: "JPG, PNG, WEBP, HEIC, PDF – bis 25 MB pro Datei",
  uploading: "Wird hochgeladen …",
  keyIntro: "Fotografiere den ausgefüllten Lösungsbogen oder tippe die Lösungen ein.",
  readWithModel: "Mit Modell lesen",
  readAgain: "Erneut lesen",
  pasteText: "Lösungen als Text einfügen",
  pasteHint: "Eine Antwort pro Zeile, z. B. „1. B“ oder „3: Berlin“.",
  replace: "Ersetzen",
  append: "Ergänzen",
  question: "Frage",
  answer: "Antwort",
  points: "Punkte",
  addRow: "Zeile hinzufügen",
  save: "Speichern",
  saved: "Gespeichert",
  remove: "Entfernen",
  cancel: "Abbrechen",
  close: "Schließen",
  keyEmpty: "Noch keine Lösungen. Lies ein Foto ein oder füge Zeilen hinzu.",
  duplicates: "Doppelte Fragen: {list}",
  maxScore: "Maximal {points} Punkte",
  status_idle: "Bereit",
  status_queued: "Wartet",
  status_processing: "Wird gelesen",
  status_done: "Fertig",
  status_error: "Fehler",
  grouping: "Wie sind die Dateien aufgeteilt?",
  grouping_file: "Eine Datei pro Person",
  grouping_page: "Eine Seite pro Person",
  grouping_single: "Alles gehört zu einer Person",
  readPending: "Neue lesen",
  readAll: "Alle neu lesen",
  stopJobs: "Lesen stoppen",
  participantsEmpty: "Noch keine Bögen. Lade Fotos hoch oder nutze dein Handy.",
  participant: "Teilnehmende Person {n}",
  name: "Name",
  score: "Punkte",
  percent: "Prozent",
  review: "Prüfen",
  details: "Details",
  delete: "Löschen",
  deleteConfirm: "Diesen Bogen löschen?",
  verdict_correct: "Richtig",
  verdict_incorrect: "Falsch",
  verdict_review: "Prüfen",
  verdict_missing: "Fehlt",
  expected: "Erwartet",
  given: "Gegeben",
  markCorrect: "Als richtig werten",
  markIncorrect: "Als falsch werten",
  resetVerdict: "Automatisch",
  editAnswers: "Antworten bearbeiten",
  addPages: "Seiten hinzufügen",
  extraAnswers: "Zusätzliche Antworten ohne Frage im Schlüssel",
  needKey: "Lege zuerst den Lösungsschlüssel fest.",
  graded: "Bewertet",
  average: "Durchschnitt",
  best: "Beste",
  worst: "Schwächste",
  pendingReview: "Offene Prüfungen",
  perQuestion: "Pro Frage",
  rate: "Quote",
  exportSummary: "CSV: Übersicht",
  exportDetail: "CSV: Alle Antworten",
  exported: "Datei gespeichert.",
  phoneTitle: "Fotos mit dem Handy",
  phoneIntro:
    "Scanne den QR-Code mit der Handykamera. Handy und Computer müssen im selben WLAN sein. Die Verbindung endet nach 30 Minuten ohne Upload.",
  phoneTarget: "Fotos landen bei:",
  phoneNoNetwork: "Kein lokales Netzwerk gefunden. Verbinde den Computer mit einem WLAN.",
  phoneUploads: "{n} Uploads empfangen",
  phoneStop: "Verbindung beenden",
  phoneFirewall: "Auf dem Mac fragt macOS beim ersten Mal, ob Exan Geräte im lokalen Netzwerk finden darf – bitte erlauben.",
  runtime: "Lokale Modell-Laufzeit",
  runtimeOllama: "Ollama (empfohlen)",
  runtimeOpenAI: "LM Studio / llama.cpp (OpenAI-kompatibel)",
  serverUrl: "Server-Adresse",
  reachable: "Verbunden ({version})",
  unreachable: "Nicht erreichbar",
  installOllama: "Ollama herunterladen",
  installLmStudio: "LM Studio herunterladen",
  modelGuide: "Welche Modelle?",
  model: "Modell",
  chooseModel: "Modell wählen …",
  installed: "Installierte Modelle",
  suggested: "Empfohlene kleine Modelle",
  download: "Herunterladen",
  downloading: "Lädt {model} … {progress}",
  use: "Verwenden",
  inUse: "Aktiv",
  recommended: "Empfohlen",
  needsRam: "ab {gb} GB RAM · {size} GB Download",
  extractionMode: "Lesemodus",
  mode_auto: "Automatisch",
  mode_structured: "Strukturiert (JSON)",
  mode_ocr: "OCR + Auswertung",
  maxImageSide: "Maximale Bildgröße (px)",
  timeout: "Zeitlimit pro Seite (s)",
  language: "Sprache",
  refresh: "Aktualisieren",
  errorTitle: "Etwas ist schiefgelaufen",
  uploadErrors: "Nicht übernommen:",
  privacy: "Alles bleibt auf diesem Computer. Nichts wird gespeichert, wenn du Exan schließt.",
};

export type MessageKey = keyof typeof de;

const en: Record<MessageKey, string> = {
  appTagline: "Correct exams locally",
  stepKey: "Answer key",
  stepParticipants: "Participants",
  stepResults: "Results",
  settings: "Settings",
  newSession: "New correction",
  newSessionConfirm: "Delete all photos, answers and results of this correction?",
  engineStarting: "Exan is starting …",
  engineFailed: "The local engine is not running.",
  engineRestart: "Restart",
  setupNeeded: "Set up a local model first so Exan can read photos.",
  openSettings: "Open settings",
  dropHere: "Drop photos or PDFs here or",
  choose: "choose files",
  fromPhone: "Take photos with your phone",
  formats: "JPG, PNG, WEBP, HEIC, PDF – up to 25 MB per file",
  uploading: "Uploading …",
  keyIntro: "Take a photo of the completed answer sheet or type the answers.",
  readWithModel: "Read with model",
  readAgain: "Read again",
  pasteText: "Paste answers as text",
  pasteHint: "One answer per line, e.g. “1. B” or “3: Berlin”.",
  replace: "Replace",
  append: "Append",
  question: "Question",
  answer: "Answer",
  points: "Points",
  addRow: "Add row",
  save: "Save",
  saved: "Saved",
  remove: "Remove",
  cancel: "Cancel",
  close: "Close",
  keyEmpty: "No answers yet. Read a photo or add rows.",
  duplicates: "Duplicate questions: {list}",
  maxScore: "Maximum {points} points",
  status_idle: "Ready",
  status_queued: "Waiting",
  status_processing: "Reading",
  status_done: "Done",
  status_error: "Error",
  grouping: "How are the files split?",
  grouping_file: "One file per person",
  grouping_page: "One page per person",
  grouping_single: "Everything belongs to one person",
  readPending: "Read new",
  readAll: "Read all again",
  stopJobs: "Stop reading",
  participantsEmpty: "No sheets yet. Upload photos or use your phone.",
  participant: "Participant {n}",
  name: "Name",
  score: "Points",
  percent: "Percent",
  review: "Review",
  details: "Details",
  delete: "Delete",
  deleteConfirm: "Delete this sheet?",
  verdict_correct: "Correct",
  verdict_incorrect: "Wrong",
  verdict_review: "Review",
  verdict_missing: "Missing",
  expected: "Expected",
  given: "Given",
  markCorrect: "Count as correct",
  markIncorrect: "Count as wrong",
  resetVerdict: "Automatic",
  editAnswers: "Edit answers",
  addPages: "Add pages",
  extraAnswers: "Extra answers without a question in the key",
  needKey: "Set up the answer key first.",
  graded: "Graded",
  average: "Average",
  best: "Best",
  worst: "Lowest",
  pendingReview: "Open reviews",
  perQuestion: "Per question",
  rate: "Rate",
  exportSummary: "CSV: summary",
  exportDetail: "CSV: all answers",
  exported: "File saved.",
  phoneTitle: "Photos from your phone",
  phoneIntro:
    "Scan the QR code with your phone camera. Phone and computer must be on the same Wi-Fi. The connection ends after 30 minutes without uploads.",
  phoneTarget: "Photos go to:",
  phoneNoNetwork: "No local network found. Connect this computer to a Wi-Fi network.",
  phoneUploads: "{n} uploads received",
  phoneStop: "End connection",
  phoneFirewall: "On a Mac, macOS asks the first time whether Exan may find devices on your local network – please allow it.",
  runtime: "Local model runtime",
  runtimeOllama: "Ollama (recommended)",
  runtimeOpenAI: "LM Studio / llama.cpp (OpenAI-compatible)",
  serverUrl: "Server address",
  reachable: "Connected ({version})",
  unreachable: "Not reachable",
  installOllama: "Download Ollama",
  installLmStudio: "Download LM Studio",
  modelGuide: "Which models?",
  model: "Model",
  chooseModel: "Choose a model …",
  installed: "Installed models",
  suggested: "Suggested small models",
  download: "Download",
  downloading: "Downloading {model} … {progress}",
  use: "Use",
  inUse: "Active",
  recommended: "Recommended",
  needsRam: "{gb} GB RAM or more · {size} GB download",
  extractionMode: "Reading mode",
  mode_auto: "Automatic",
  mode_structured: "Structured (JSON)",
  mode_ocr: "OCR + parsing",
  maxImageSide: "Maximum image size (px)",
  timeout: "Time limit per page (s)",
  language: "Language",
  refresh: "Refresh",
  errorTitle: "Something went wrong",
  uploadErrors: "Not added:",
  privacy: "Everything stays on this computer. Nothing is kept after you close Exan.",
};

const dictionaries: Record<Language, Record<MessageKey, string>> = { de, en };

export type Translate = (key: MessageKey, vars?: Record<string, string | number>) => string;

export function translate(language: Language, key: MessageKey, vars?: Record<string, string | number>): string {
  const template = dictionaries[language][key] ?? de[key];
  return template.replace(/\{(\w+)\}/g, (_, name: string) => String(vars?.[name] ?? `{${name}}`));
}

export function storedLanguage(): Language {
  try {
    const value = localStorage.getItem(LANGUAGE_STORAGE_KEY);
    if (value === "de" || value === "en") return value;
  } catch {
    // storage unavailable
  }
  return navigator.language?.toLowerCase().startsWith("de") ? "de" : "en";
}

interface I18n {
  language: Language;
  setLanguage: (language: Language) => void;
  t: Translate;
}

const I18nContext = createContext<I18n | null>(null);

export function I18nProvider({ children, initial }: { children: ReactNode; initial?: Language }) {
  const [language, setLanguageState] = useState<Language>(() => initial ?? storedLanguage());
  const setLanguage = useCallback((next: Language) => {
    setLanguageState(next);
    try {
      localStorage.setItem(LANGUAGE_STORAGE_KEY, next);
    } catch {
      // storage unavailable
    }
    document.documentElement.lang = next;
  }, []);
  const value = useMemo<I18n>(
    () => ({ language, setLanguage, t: (key, vars) => translate(language, key, vars) }),
    [language, setLanguage],
  );
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18n {
  const context = useContext(I18nContext);
  if (!context) throw new Error("useI18n must be used inside I18nProvider");
  return context;
}
