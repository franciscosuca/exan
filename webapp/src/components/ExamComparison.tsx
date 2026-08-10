import { useState, useEffect } from 'react';
import { FileDropzone } from './FileDropzone';
import { ProviderSelector } from './ProviderSelector';
import { StepIndicator } from './StepIndicator';
import { ComparisonResults } from './ComparisonResults';
import {
  getProviders,
  getProviderModels,
  uploadExamTemplate,
  uploadAnswerKey,
  updateAnswerKey,
  compareStudentExams,
  type ProviderConfig,
  type ProviderModel,
  type ExamStructure,
  type AnswerKey,
  type Answer,
  type ComparisonResult,
} from '../lib/api';
import { useLanguage } from '../lib/i18n';
import { ArrowRight, Loader2, Plus, RotateCcw } from 'lucide-react';

interface ExamComparisonProps {
  onBack: () => void;
}

function answerCoversQuestion(expectedQuestionNumber: string, detectedQuestionNumber: string) {
  if (expectedQuestionNumber === detectedQuestionNumber) return true;
  if (!detectedQuestionNumber.startsWith(expectedQuestionNumber)) return false;

  const suffix = detectedQuestionNumber.slice(expectedQuestionNumber.length);
  return /^[a-z]|^[-._]/.test(suffix);
}

export function ExamComparison({ onBack }: ExamComparisonProps) {
  const { t } = useLanguage();
  const STEPS = [t('examComparison.step1'), t('examComparison.step2'), t('examComparison.step3')];
  const [providers, setProviders] = useState<ProviderConfig[]>([]);
  const [selectedProvider, setSelectedProvider] = useState('');
  const [models, setModels] = useState<ProviderModel[]>([]);
  const [selectedModel, setSelectedModel] = useState('');
  const [modelsLoading, setModelsLoading] = useState(false);
  const [modelsError, setModelsError] = useState<string | null>(null);
  const [criteria, setCriteria] = useState('');
  const [currentStep, setCurrentStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [examStructure, setExamStructure] = useState<ExamStructure | null>(null);
  const [answerKey, setAnswerKey] = useState<AnswerKey | null>(null);
  const [editableAnswers, setEditableAnswers] = useState<Answer[]>([]);
  const [comparisonResults, setComparisonResults] = useState<ComparisonResult[]>([]);

  useEffect(() => {
    getProviders()
      .then((p) => {
        setProviders(p);
      })
      .catch(() => setError(t('common.cannotConnect')));
  }, [t]);

  const handleProviderSelect = (provider: string) => {
    setSelectedProvider(provider);
    setSelectedModel('');
    setModels([]);
    setModelsError(null);

    if (provider !== 'gemini') return;

    setModelsLoading(true);
    getProviderModels(provider)
      .then(setModels)
      .catch((e: unknown) => {
        setModelsError(e instanceof Error ? e.message : t('common.modelLoadError'));
      })
      .finally(() => setModelsLoading(false));
  };

  const canUseWorkflow = selectedProvider === 'gemini' && selectedModel.trim().length > 0;
  const expectedAnswerCount = examStructure?.questions.length ?? 0;
  const expectedQuestionNumbers = examStructure
    ? [...new Set(examStructure.questions.map((question) => String(question.number).trim()))].filter(
        Boolean
      )
    : [];
  const missingQuestionNumbers = expectedQuestionNumbers.filter(
    (expectedQuestionNumber) =>
      !editableAnswers.some((answer) =>
        answerCoversQuestion(expectedQuestionNumber, String(answer.question_number).trim())
      )
  );
  const hasMissingAnswerCount =
    editableAnswers.length === 0 ||
    editableAnswers.length < expectedAnswerCount ||
    missingQuestionNumbers.length > 0;
  const hasIncompleteAnswerValues = editableAnswers.some(
    (answer) =>
      String(answer.question_number).trim().length === 0 || answer.correct_answer.trim().length === 0
  );
  const canContinueWithAnswerKey =
    Boolean(examStructure && answerKey) && !hasMissingAnswerCount && !hasIncompleteAnswerValues;

  const requireSelection = () => {
    if (canUseWorkflow) return true;
    setError(t('common.selectionRequired'));
    return false;
  };

  const reset = () => {
    setCurrentStep(0);
    setCriteria('');
    setExamStructure(null);
    setAnswerKey(null);
    setEditableAnswers([]);
    setComparisonResults([]);
    setError(null);
  };

  const updateAnswer = (
    answerIndex: number,
    field: 'question_number' | 'correct_answer',
    value: string
  ) => {
    setEditableAnswers((currentAnswers) =>
      currentAnswers.map((answer, currentIndex) =>
        currentIndex === answerIndex ? { ...answer, [field]: value } : answer
      )
    );
  };

  const addAnswerRow = () => {
    setEditableAnswers((currentAnswers) => {
      const nextQuestionNumber =
        examStructure?.questions.find(
          (question) =>
            !currentAnswers.some(
              (answer) => String(answer.question_number) === String(question.number)
            )
        )?.number ?? '';

      return [...currentAnswers, { question_number: nextQuestionNumber, correct_answer: '' }];
    });
  };

  const retryAnswerKeyUpload = () => {
    setAnswerKey(null);
    setEditableAnswers([]);
    setError(null);
  };

  const handleExamTemplate = async (files: File[]) => {
    if (!requireSelection() || files.length === 0) return;
    setLoading(true);
    setError(null);
    try {
      const result = await uploadExamTemplate(files[0], selectedProvider, criteria, selectedModel);
      setExamStructure(result);
      setCurrentStep(1);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t('examComparison.step1.error'));
    } finally {
      setLoading(false);
    }
  };

  const handleAnswerKey = async (files: File[]) => {
    if (!requireSelection() || !examStructure || files.length === 0) return;
    setLoading(true);
    setError(null);
    try {
      const result = await uploadAnswerKey(files[0], examStructure.id, selectedProvider, selectedModel);
      setAnswerKey(result);
      setEditableAnswers(result.answers);
      setCurrentStep(1);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t('examComparison.step2.error'));
    } finally {
      setLoading(false);
    }
  };

  const continueToStudentExams = async () => {
    if (!requireSelection() || !examStructure || !answerKey || !canContinueWithAnswerKey) return;
    setLoading(true);
    setError(null);
    try {
      const result = await updateAnswerKey(examStructure.id, editableAnswers);
      setAnswerKey(result);
      setEditableAnswers(result.answers);
      setCurrentStep(2);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t('examComparison.step2.saveError'));
    } finally {
      setLoading(false);
    }
  };

  const handleStudentExams = async (files: File[]) => {
    if (!requireSelection() || !examStructure || !answerKey || files.length === 0) return;
    setLoading(true);
    setError(null);
    try {
      const results = await compareStudentExams(files, examStructure.id, selectedProvider, selectedModel);
      setComparisonResults(results);
      setCurrentStep(3);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t('examComparison.step3.error'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="mb-6 flex items-center gap-3">
        <button
          onClick={onBack}
          className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100"
        >
          {t('common.back')}
        </button>
        <button
          onClick={reset}
          className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100"
        >
          <RotateCcw className="h-4 w-4" /> {t('common.startOver')}
        </button>
      </div>

      <div className="mb-8">
        <StepIndicator steps={STEPS} currentStep={currentStep} />
      </div>

      <div className="mb-8">
        <label className="mb-2 block text-sm font-medium text-gray-700">{t('common.aiProvider')}</label>
        <ProviderSelector
          providers={providers}
          selected={selectedProvider}
          onSelect={handleProviderSelect}
        />
        {selectedProvider && (
          <div className="mt-4">
            <label htmlFor="exam-model" className="mb-2 block text-sm font-medium text-gray-700">
              {t('common.aiModel')}
            </label>
            {modelsLoading && <p className="text-sm text-gray-500">{t('common.loadingModels')}</p>}
            {modelsError && (
              <p className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                {t('common.modelLoadError')}: {modelsError}
              </p>
            )}
            {!modelsLoading && !modelsError && models.length === 0 && (
              <p className="text-sm text-amber-700">{t('common.noModels')}</p>
            )}
            {!modelsLoading && !modelsError && models.length > 0 && (
              <select
                id="exam-model"
                value={selectedModel}
                onChange={(event) => setSelectedModel(event.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
              >
                <option value="">{t('common.selectModel')}</option>
                {models.map((model) => (
                  <option key={model.id} value={model.id}>
                    {model.display_name}
                  </option>
                ))}
              </select>
            )}
          </div>
        )}
      </div>

      {error && (
        <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {loading && (
        <div className="mb-6 flex items-center justify-center gap-2 rounded-lg bg-blue-50 p-6 text-blue-700">
          <Loader2 className="h-5 w-5 animate-spin" />
          <span>{t('examComparison.processing', { provider: selectedProvider })}</span>
        </div>
      )}

      {!loading && currentStep === 0 && (
        <div className="space-y-4">
          <h2 className="text-xl font-semibold text-gray-900">{t('examComparison.step1.title')}</h2>
          <p className="text-gray-600">
            {t('examComparison.step1.description')}
          </p>
          <div className="space-y-2">
            <label htmlFor="exam-criteria" className="block text-sm font-medium text-gray-700">
              {t('examComparison.step1.criteriaLabel')}
            </label>
            <textarea
              id="exam-criteria"
              value={criteria}
              onChange={(event) => setCriteria(event.target.value)}
              placeholder={t('examComparison.step1.criteriaPlaceholder')}
              rows={3}
              disabled={!canUseWorkflow}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
            />
            <p className="text-sm text-gray-500">
              {t('examComparison.step1.criteriaDescription')}
            </p>
          </div>
          <FileDropzone
            onFiles={handleExamTemplate}
            disabled={!canUseWorkflow}
            label={t('examComparison.step1.dropLabel')}
            description={t('examComparison.step1.dropDescription')}
          />
        </div>
      )}

      {!loading && currentStep === 1 && (
        <div className="space-y-4">
          {!answerKey ? (
            <>
              <h2 className="text-xl font-semibold text-gray-900">{t('examComparison.step2.title')}</h2>
              <p className="text-gray-600">
                {t('examComparison.step2.description')}
              </p>
              {examStructure && (
                <div className="rounded-lg border border-green-200 bg-green-50 p-4 text-sm text-green-800">
                  {t('examComparison.step2.detected', {
                    count: examStructure.questions.length,
                    filename: examStructure.filename,
                  })}
                </div>
              )}
              <FileDropzone
                onFiles={handleAnswerKey}
                disabled={!canUseWorkflow}
                label={t('examComparison.step2.dropLabel')}
                description={t('examComparison.step2.dropDescription')}
              />
            </>
          ) : (
            <>
              <h2 className="text-xl font-semibold text-gray-900">
                {t('examComparison.step2.reviewTitle')}
              </h2>
              <p className="text-gray-600">
                {t('examComparison.step2.reviewDescription')}
              </p>
              {examStructure && (
                <div className="rounded-lg border border-green-200 bg-green-50 p-4 text-sm text-green-800">
                  {t('examComparison.step2.detected', {
                    count: examStructure.questions.length,
                    filename: examStructure.filename,
                  })}
                </div>
              )}
              <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 text-sm text-blue-800">
                {t('examComparison.step2.extracted', { count: editableAnswers.length })}
              </div>
              {hasMissingAnswerCount && (
                <div
                  role="alert"
                  className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800"
                >
                  <p className="font-medium">{t('examComparison.step2.incompleteTitle')}</p>
                  <p className="mt-1">
                    {editableAnswers.length >= expectedAnswerCount && missingQuestionNumbers.length > 0
                      ? t('examComparison.step2.missingQuestions', {
                          questions: missingQuestionNumbers.join(', '),
                        })
                      : t('examComparison.step2.incompleteDescription', {
                          extracted: editableAnswers.length,
                          expected: expectedAnswerCount,
                        })}
                  </p>
                  <button
                    type="button"
                    onClick={retryAnswerKeyUpload}
                    className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-amber-300 px-3 py-1.5 font-medium text-amber-900 hover:bg-amber-100"
                  >
                    <RotateCcw className="h-4 w-4" />
                    {t('examComparison.step2.retry')}
                  </button>
                </div>
              )}
              <div className="overflow-x-auto rounded-lg border border-gray-200">
                <table className="min-w-full text-left text-sm">
                  <caption className="sr-only">{t('examComparison.step2.tableCaption')}</caption>
                  <thead className="bg-gray-50 text-xs uppercase text-gray-500">
                    <tr>
                      <th scope="col" className="px-4 py-3 font-medium">
                        {t('examComparison.step2.questionNumberHeader')}
                      </th>
                      <th scope="col" className="px-4 py-3 font-medium">
                        {t('examComparison.step2.correctAnswerHeader')}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {editableAnswers.length === 0 ? (
                      <tr>
                        <td colSpan={2} className="px-4 py-4 text-gray-500">
                          {t('examComparison.step2.noAnswers')}
                        </td>
                      </tr>
                    ) : (
                      editableAnswers.map((answer, answerIndex) => (
                        <tr key={`answer-${answerIndex}`} className="border-t border-gray-100">
                          <td className="px-4 py-3 align-top">
                            <label
                              htmlFor={`answer-question-number-${answerIndex}`}
                              className="sr-only"
                            >
                              {t('examComparison.step2.questionNumberLabel', {
                                number: answerIndex + 1,
                              })}
                            </label>
                            <input
                              id={`answer-question-number-${answerIndex}`}
                              type="text"
                              value={String(answer.question_number)}
                              onChange={(event) =>
                                updateAnswer(answerIndex, 'question_number', event.target.value)
                              }
                              aria-invalid={String(answer.question_number).trim().length === 0}
                              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-gray-900 shadow-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
                            />
                          </td>
                          <td className="px-4 py-3 align-top">
                            <label
                              htmlFor={`answer-correct-answer-${answerIndex}`}
                              className="sr-only"
                            >
                              {t('examComparison.step2.correctAnswerLabel', {
                                number: answerIndex + 1,
                              })}
                            </label>
                            <input
                              id={`answer-correct-answer-${answerIndex}`}
                              type="text"
                              value={answer.correct_answer}
                              onChange={(event) =>
                                updateAnswer(answerIndex, 'correct_answer', event.target.value)
                              }
                              aria-invalid={answer.correct_answer.trim().length === 0}
                              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-gray-900 shadow-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
                            />
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <button
                  type="button"
                  onClick={addAnswerRow}
                  className="inline-flex items-center justify-center gap-1.5 rounded-lg border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  <Plus className="h-4 w-4" />
                  {t('examComparison.step2.addAnswer')}
                </button>
                <button
                  type="button"
                  onClick={continueToStudentExams}
                  disabled={!canContinueWithAnswerKey}
                  className="inline-flex items-center justify-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {t('examComparison.step2.continue')}
                  <ArrowRight className="h-4 w-4" />
                </button>
              </div>
              {hasIncompleteAnswerValues && (
                <p role="alert" className="text-sm text-amber-700">
                  {t('examComparison.step2.completeAnswers')}
                </p>
              )}
            </>
          )}
        </div>
      )}

      {!loading && currentStep === 2 && (
        <div className="space-y-4">
          <h2 className="text-xl font-semibold text-gray-900">{t('examComparison.step3.title')}</h2>
          <p className="text-gray-600">
            {t('examComparison.step3.description')}
          </p>
          {answerKey && (
            <div className="rounded-lg border border-green-200 bg-green-50 p-4 text-sm text-green-800">
              {t('examComparison.step3.loaded', { count: answerKey.answers.length })}
            </div>
          )}
          <FileDropzone
            onFiles={handleStudentExams}
            disabled={!canUseWorkflow}
            multiple
            label={t('examComparison.step3.dropLabel')}
            description={t('examComparison.step3.dropDescription')}
          />
        </div>
      )}

      {!loading && currentStep === 3 && <ComparisonResults results={comparisonResults} />}
    </div>
  );
}
