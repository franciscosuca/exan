import { useState, useEffect } from 'react';
import { FileDropzone } from './FileDropzone';
import { ProviderSelector } from './ProviderSelector';
import { StepIndicator } from './StepIndicator';
import { ComparisonResults } from './ComparisonResults';
import {
  getProviders,
  uploadExamTemplate,
  uploadAnswerKey,
  compareStudentExams,
  type ProviderConfig,
  type ExamStructure,
  type AnswerKey,
  type ComparisonResult,
} from '../lib/api';
import { useLanguage } from '../lib/i18n';
import { Loader2, RotateCcw } from 'lucide-react';

interface ExamComparisonProps {
  onBack: () => void;
}

export function ExamComparison({ onBack }: ExamComparisonProps) {
  const { t } = useLanguage();
  const STEPS = [t('examComparison.step1'), t('examComparison.step2'), t('examComparison.step3')];
  const [providers, setProviders] = useState<ProviderConfig[]>([]);
  const [selectedProvider, setSelectedProvider] = useState('');
  const [criteria, setCriteria] = useState('');
  const [currentStep, setCurrentStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [examStructure, setExamStructure] = useState<ExamStructure | null>(null);
  const [answerKey, setAnswerKey] = useState<AnswerKey | null>(null);
  const [comparisonResults, setComparisonResults] = useState<ComparisonResult[]>([]);

  useEffect(() => {
    getProviders()
      .then((p) => {
        setProviders(p);
        const first = p.find((x) => x.available);
        if (first) setSelectedProvider(first.provider);
      })
      .catch(() => setError(t('common.cannotConnect')));
  }, [t]);

  const reset = () => {
    setCurrentStep(0);
    setCriteria('');
    setExamStructure(null);
    setAnswerKey(null);
    setComparisonResults([]);
    setError(null);
  };

  const handleExamTemplate = async (files: File[]) => {
    setLoading(true);
    setError(null);
    try {
      const result = await uploadExamTemplate(files[0], selectedProvider, criteria);
      setExamStructure(result);
      setCurrentStep(1);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t('examComparison.step1.error'));
    } finally {
      setLoading(false);
    }
  };

  const handleAnswerKey = async (files: File[]) => {
    if (!examStructure) return;
    setLoading(true);
    setError(null);
    try {
      const result = await uploadAnswerKey(files[0], examStructure.id, selectedProvider);
      setAnswerKey(result);
      setCurrentStep(2);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t('examComparison.step2.error'));
    } finally {
      setLoading(false);
    }
  };

  const handleStudentExams = async (files: File[]) => {
    if (!examStructure) return;
    setLoading(true);
    setError(null);
    try {
      const results = await compareStudentExams(files, examStructure.id, selectedProvider);
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
          onSelect={setSelectedProvider}
        />
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
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
            />
            <p className="text-sm text-gray-500">
              {t('examComparison.step1.criteriaDescription')}
            </p>
          </div>
          <FileDropzone
            onFiles={handleExamTemplate}
            label={t('examComparison.step1.dropLabel')}
            description={t('examComparison.step1.dropDescription')}
          />
        </div>
      )}

      {!loading && currentStep === 1 && (
        <div className="space-y-4">
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
            label={t('examComparison.step2.dropLabel')}
            description={t('examComparison.step2.dropDescription')}
          />
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
