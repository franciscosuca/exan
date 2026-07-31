import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

export type Language = 'de' | 'en';

export const LANGUAGE_STORAGE_KEY = 'exan_language';
export const DEFAULT_LANGUAGE: Language = 'de';

const translations = {
  en: {
    'app.name': 'Exan',
    'app.header.examComparison': 'Exam Comparison',
    'app.header.batchEvaluation': 'Batch Evaluation',
    'app.logout': 'Logout',
    'app.landing.title': 'Welcome to Exan',
    'app.landing.subtitle': 'AI-powered exam scanning, grading, and evaluation',
    'app.landing.examComparison.title': 'Exam Comparison',
    'app.landing.examComparison.description':
      'Upload an exam template and answer key, then grade student exams by comparing answers against the correct solutions.',
    'app.landing.batchEvaluation.title': 'Batch Evaluation',
    'app.landing.batchEvaluation.description':
      'Upload multiple exams (PDF or Word) and evaluate them against grammar correctness and custom criteria you define.',
    'app.landing.getStarted': 'Get started →',

    'auth.login.title': 'Login',
    'auth.login.username': 'USERNAME',
    'auth.login.password': 'PASSWORD',
    'auth.login.submit': 'Sign In',
    'auth.login.submitting': 'Signing in...',
    'auth.login.noAccount': 'No account?',
    'auth.login.register': 'Register',
    'auth.register.title': 'Register',
    'auth.register.username': 'USERNAME',
    'auth.register.password': 'PASSWORD',
    'auth.register.repeatPassword': 'REPEAT PASSWORD',
    'auth.register.submit': 'Create Account',
    'auth.register.submitting': 'Creating account...',
    'auth.register.haveAccount': 'Already have an account?',
    'auth.register.login': 'Login',
    'auth.register.passwordMismatch': 'Passwords do not match',

    'common.back': '← Back',
    'common.startOver': 'Start Over',
    'common.reset': 'Reset',
    'common.aiProvider': 'AI Provider',
    'common.cannotConnect': 'Cannot connect to backend. Is the server running?',
    'common.noProviders':
      'No AI providers available. Please configure at least one provider in the backend.',
    'common.local': 'local',

    'examComparison.step1': 'Upload Exam Template',
    'examComparison.step2': 'Upload Answer Key',
    'examComparison.step3': 'Grade Student Exams',
    'examComparison.processing': 'Processing with {provider}...',
    'examComparison.step1.title': 'Step 1: Upload Empty Exam',
    'examComparison.step1.description':
      'Upload a PDF or image of the blank exam template. The AI will analyze its structure and identify all questions.',
    'examComparison.step1.dropLabel': 'Drop exam template here',
    'examComparison.step1.dropDescription': 'PDF or image (PNG, JPG, WebP)',
    'examComparison.step1.error': 'Failed to process exam template',
    'examComparison.step2.title': 'Step 2: Upload Answer Key',
    'examComparison.step2.description':
      'Upload the exam with the correct answers filled in. This will be used to grade student responses.',
    'examComparison.step2.detected': '✓ Detected {count} questions in "{filename}"',
    'examComparison.step2.dropLabel': 'Drop answer key here',
    'examComparison.step2.dropDescription': 'PDF or image with correct answers',
    'examComparison.step2.error': 'Failed to process answer key',
    'examComparison.step3.title': 'Step 3: Upload Student Exams',
    'examComparison.step3.description':
      'Upload one or more completed exams from students. Each file will be graded individually.',
    'examComparison.step3.loaded': '✓ Answer key loaded with {count} answers',
    'examComparison.step3.dropLabel': 'Drop student exams here',
    'examComparison.step3.dropDescription': 'Multiple files supported (PDF or images)',
    'examComparison.step3.error': 'Failed to grade student exams',

    'gradingResults.title': 'Grading Results',
    'gradingResults.points': '{score}/{max} points',
    'gradingResults.viewBreakdown': 'View question breakdown',
    'gradingResults.noAnswer': '(no answer)',
    'gradingResults.pts': '{earned}/{possible} pts',
    'gradingResults.correct': 'Correct',
    'gradingResults.incorrect': 'Incorrect',

    'batchEvaluation.uploadExams': 'Upload Exams',
    'batchEvaluation.uploadExamsDescription':
      'Upload one or more exams in PDF or Word format. Each file will be evaluated individually.',
    'batchEvaluation.dropLabel': 'Drop exam files here',
    'batchEvaluation.dropDescription': 'PDF or Word documents (.pdf, .docx, .doc)',
    'batchEvaluation.filesSelected': '{count} file(s) selected:',
    'batchEvaluation.criteria': 'Evaluation Criteria',
    'batchEvaluation.grammarCorrection': 'Grammar Correction',
    'batchEvaluation.default': 'Default',
    'batchEvaluation.language': 'Language',
    'batchEvaluation.customCriteria': 'Custom Criteria #{index}',
    'batchEvaluation.criteriaName': 'Criteria name (e.g., Argument Quality)',
    'batchEvaluation.criteriaDescription': 'Description — what should the AI evaluate?',
    'batchEvaluation.criteriaZero': 'What does 0% look like?',
    'batchEvaluation.criteriaHundred': 'What does 100% look like?',
    'batchEvaluation.addCriteria': 'Add Custom Criteria',
    'batchEvaluation.evaluate': 'Evaluate {count} File{plural}',
    'batchEvaluation.evaluating': 'Evaluating {count} file(s) with {provider}...',
    'batchEvaluation.noFiles': 'Please upload at least one file',
    'batchEvaluation.noCriteria': 'Please select at least one evaluation criteria',
    'batchEvaluation.error': 'Evaluation failed',
    'batchEvaluation.newEvaluation': 'New Evaluation',

    'batchResults.title': 'Evaluation Results',
    'batchResults.filesEvaluated': '{count} file(s) evaluated',
    'batchResults.overall': 'Overall',

    'fileDropzone.dropping': 'Drop files here...',

    'language.en': 'English',
    'language.de': 'German',
  },
  de: {
    'app.name': 'Exan',
    'app.header.examComparison': 'Prüfungsvergleich',
    'app.header.batchEvaluation': 'Stapelauswertung',
    'app.logout': 'Abmelden',
    'app.landing.title': 'Willkommen bei Exan',
    'app.landing.subtitle': 'KI-gestütztes Scannen, Bewerten und Auswerten von Prüfungen',
    'app.landing.examComparison.title': 'Prüfungsvergleich',
    'app.landing.examComparison.description':
      'Lade eine Prüfungsvorlage und einen Lösungsschlüssel hoch und bewerte Schülerprüfungen durch den Vergleich der Antworten mit den korrekten Lösungen.',
    'app.landing.batchEvaluation.title': 'Stapelauswertung',
    'app.landing.batchEvaluation.description':
      'Lade mehrere Prüfungen (PDF oder Word) hoch und bewerte sie anhand von Grammatikkorrektheit und selbst definierten Kriterien.',
    'app.landing.getStarted': 'Loslegen →',

    'auth.login.title': 'Anmelden',
    'auth.login.username': 'BENUTZERNAME',
    'auth.login.password': 'PASSWORT',
    'auth.login.submit': 'Anmelden',
    'auth.login.submitting': 'Anmeldung läuft...',
    'auth.login.noAccount': 'Kein Konto?',
    'auth.login.register': 'Registrieren',
    'auth.register.title': 'Registrieren',
    'auth.register.username': 'BENUTZERNAME',
    'auth.register.password': 'PASSWORT',
    'auth.register.repeatPassword': 'PASSWORT WIEDERHOLEN',
    'auth.register.submit': 'Konto erstellen',
    'auth.register.submitting': 'Konto wird erstellt...',
    'auth.register.haveAccount': 'Bereits ein Konto?',
    'auth.register.login': 'Anmelden',
    'auth.register.passwordMismatch': 'Passwörter stimmen nicht überein',

    'common.back': '← Zurück',
    'common.startOver': 'Neu beginnen',
    'common.reset': 'Zurücksetzen',
    'common.aiProvider': 'KI-Anbieter',
    'common.cannotConnect': 'Verbindung zum Server nicht möglich. Läuft der Server?',
    'common.noProviders':
      'Keine KI-Anbieter verfügbar. Bitte konfiguriere mindestens einen Anbieter im Backend.',
    'common.local': 'lokal',

    'examComparison.step1': 'Prüfungsvorlage hochladen',
    'examComparison.step2': 'Lösungsschlüssel hochladen',
    'examComparison.step3': 'Schülerprüfungen bewerten',
    'examComparison.processing': 'Verarbeitung mit {provider}...',
    'examComparison.step1.title': 'Schritt 1: Leere Prüfung hochladen',
    'examComparison.step1.description':
      'Lade ein PDF oder Bild der leeren Prüfungsvorlage hoch. Die KI analysiert die Struktur und erkennt alle Fragen.',
    'examComparison.step1.dropLabel': 'Prüfungsvorlage hier ablegen',
    'examComparison.step1.dropDescription': 'PDF oder Bild (PNG, JPG, WebP)',
    'examComparison.step1.error': 'Verarbeitung der Prüfungsvorlage fehlgeschlagen',
    'examComparison.step2.title': 'Schritt 2: Lösungsschlüssel hochladen',
    'examComparison.step2.description':
      'Lade die Prüfung mit den korrekten Antworten hoch. Diese wird zur Bewertung der Schülerantworten verwendet.',
    'examComparison.step2.detected': '✓ {count} Fragen in "{filename}" erkannt',
    'examComparison.step2.dropLabel': 'Lösungsschlüssel hier ablegen',
    'examComparison.step2.dropDescription': 'PDF oder Bild mit korrekten Antworten',
    'examComparison.step2.error': 'Verarbeitung des Lösungsschlüssels fehlgeschlagen',
    'examComparison.step3.title': 'Schritt 3: Schülerprüfungen hochladen',
    'examComparison.step3.description':
      'Lade eine oder mehrere ausgefüllte Prüfungen von Schülern hoch. Jede Datei wird einzeln bewertet.',
    'examComparison.step3.loaded': '✓ Lösungsschlüssel mit {count} Antworten geladen',
    'examComparison.step3.dropLabel': 'Schülerprüfungen hier ablegen',
    'examComparison.step3.dropDescription': 'Mehrere Dateien möglich (PDF oder Bilder)',
    'examComparison.step3.error': 'Bewertung der Schülerprüfungen fehlgeschlagen',

    'gradingResults.title': 'Bewertungsergebnisse',
    'gradingResults.points': '{score}/{max} Punkte',
    'gradingResults.viewBreakdown': 'Fragenaufschlüsselung anzeigen',
    'gradingResults.noAnswer': '(keine Antwort)',
    'gradingResults.pts': '{earned}/{possible} Pkt.',
    'gradingResults.correct': 'Richtig',
    'gradingResults.incorrect': 'Falsch',

    'batchEvaluation.uploadExams': 'Prüfungen hochladen',
    'batchEvaluation.uploadExamsDescription':
      'Lade eine oder mehrere Prüfungen im PDF- oder Word-Format hoch. Jede Datei wird einzeln ausgewertet.',
    'batchEvaluation.dropLabel': 'Prüfungsdateien hier ablegen',
    'batchEvaluation.dropDescription': 'PDF- oder Word-Dokumente (.pdf, .docx, .doc)',
    'batchEvaluation.filesSelected': '{count} Datei(en) ausgewählt:',
    'batchEvaluation.criteria': 'Bewertungskriterien',
    'batchEvaluation.grammarCorrection': 'Grammatikkorrektur',
    'batchEvaluation.default': 'Standard',
    'batchEvaluation.language': 'Sprache',
    'batchEvaluation.customCriteria': 'Eigenes Kriterium #{index}',
    'batchEvaluation.criteriaName': 'Kriteriumsname (z. B. Argumentqualität)',
    'batchEvaluation.criteriaDescription': 'Beschreibung — was soll die KI bewerten?',
    'batchEvaluation.criteriaZero': 'Wie sieht 0 % aus?',
    'batchEvaluation.criteriaHundred': 'Wie sehen 100 % aus?',
    'batchEvaluation.addCriteria': 'Eigenes Kriterium hinzufügen',
    'batchEvaluation.evaluate': '{count} Datei{plural} auswerten',
    'batchEvaluation.evaluating': 'Auswertung von {count} Datei(en) mit {provider}...',
    'batchEvaluation.noFiles': 'Bitte lade mindestens eine Datei hoch',
    'batchEvaluation.noCriteria': 'Bitte wähle mindestens ein Bewertungskriterium aus',
    'batchEvaluation.error': 'Auswertung fehlgeschlagen',
    'batchEvaluation.newEvaluation': 'Neue Auswertung',

    'batchResults.title': 'Auswertungsergebnisse',
    'batchResults.filesEvaluated': '{count} Datei(en) ausgewertet',
    'batchResults.overall': 'Gesamt',

    'fileDropzone.dropping': 'Dateien hier ablegen...',

    'language.en': 'Englisch',
    'language.de': 'Deutsch',
  },
} as const satisfies Record<Language, Record<string, string>>;

export type TranslationKey = keyof (typeof translations)['en'];

function interpolate(template: string, params?: Record<string, string | number>): string {
  if (!params) return template;
  return template.replace(/\{(\w+)\}/g, (match, key: string) =>
    key in params ? String(params[key]) : match
  );
}

export function readStoredLanguage(): Language {
  if (typeof window === 'undefined') return DEFAULT_LANGUAGE;
  const stored = window.localStorage.getItem(LANGUAGE_STORAGE_KEY);
  return stored === 'en' || stored === 'de' ? stored : DEFAULT_LANGUAGE;
}

interface LanguageContextValue {
  language: Language;
  setLanguage: (language: Language) => void;
  t: (key: TranslationKey, params?: Record<string, string | number>) => string;
}

const LanguageContext = createContext<LanguageContextValue | null>(null);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>(() => readStoredLanguage());

  const setLanguage = useCallback((next: Language) => {
    setLanguageState(next);
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(LANGUAGE_STORAGE_KEY, next);
    }
  }, []);

  const t = useCallback(
    (key: TranslationKey, params?: Record<string, string | number>) =>
      interpolate(translations[language][key], params),
    [language]
  );

  const value = useMemo(() => ({ language, setLanguage, t }), [language, setLanguage, t]);

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage(): LanguageContextValue {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return context;
}
