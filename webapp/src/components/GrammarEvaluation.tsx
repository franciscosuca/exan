import { useState, useEffect } from 'react';
import { FileDropzone } from './FileDropzone';
import { ProviderSelector } from './ProviderSelector';
import { GrammarResults } from './GrammarResults';
import {
  getProviders,
  getProviderModels,
  grammarEvaluate,
  type ProviderConfig,
  type ProviderModel,
  type GrammarEvaluationResponse,
} from '../lib/api';
import { useLanguage } from '../lib/i18n';
import { isFileSizeExceeded } from '../lib/file-validation';
import { Loader2, Trash2, RotateCcw } from 'lucide-react';

interface GrammarEvaluationProps {
  onBack: () => void;
}

const LANGUAGES = [
  { code: 'en', label: 'English' },
  { code: 'es', label: 'Spanish' },
  { code: 'fr', label: 'French' },
  { code: 'de', label: 'German' },
  { code: 'pt', label: 'Portuguese' },
  { code: 'it', label: 'Italian' },
  { code: 'nl', label: 'Dutch' },
  { code: 'ca', label: 'Catalan' },
];

export function GrammarEvaluation({ onBack }: GrammarEvaluationProps) {
  const { t, language: uiLanguage } = useLanguage();
  const [providers, setProviders] = useState<ProviderConfig[]>([]);
  const [selectedProvider, setSelectedProvider] = useState('');
  const [models, setModels] = useState<ProviderModel[]>([]);
  const [selectedModel, setSelectedModel] = useState('');
  const [modelsLoading, setModelsLoading] = useState(false);
  const [modelsError, setModelsError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [files, setFiles] = useState<File[]>([]);
  // Default the grammar-check language to the current webpage language, so
  // AI answers follow the language the user is browsing in.
  const [correctionLanguage, setCorrectionLanguage] = useState<string>(uiLanguage);
  const [results, setResults] = useState<GrammarEvaluationResponse | null>(null);

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

  const requireSelection = () => {
    if (canUseWorkflow) return true;
    setError(t('common.selectionRequired'));
    return false;
  };

  const reset = () => {
    setFiles([]);
    setResults(null);
    setError(null);
  };

  const handleFiles = (newFiles: File[]) => {
    if (!requireSelection()) return;
    const combinedFiles = [...files, ...newFiles];
    // TODO: This 32 MiB limit check is a temporary safeguard for Cloud Run and must be reworked later.
    if (isFileSizeExceeded(combinedFiles)) {
      setError(t('fileDropzone.sizeLimitExceeded'));
      return;
    }
    setError(null);
    setFiles(combinedFiles);
  };

  const removeFile = (index: number) => {
    setFiles(files.filter((_, i) => i !== index));
  };

  const handleEvaluate = async () => {
    if (!requireSelection()) return;
    if (files.length === 0) {
      setError(t('grammarEvaluation.noFiles'));
      return;
    }
    // TODO: This 32 MiB limit check is a temporary safeguard for Cloud Run and must be reworked later.
    if (isFileSizeExceeded(files)) {
      setError(t('fileDropzone.sizeLimitExceeded'));
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await grammarEvaluate(
        files,
        selectedProvider,
        correctionLanguage,
        uiLanguage,
        selectedModel
      );
      setResults(response);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t('grammarEvaluation.error'));
    } finally {
      setLoading(false);
    }
  };

  if (results) {
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
            <RotateCcw className="h-4 w-4" /> {t('grammarEvaluation.newEvaluation')}
          </button>
        </div>
        <GrammarResults response={results} />
      </div>
    );
  }

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
          <RotateCcw className="h-4 w-4" /> {t('common.reset')}
        </button>
      </div>

      {/* Provider Selection */}
      <div className="mb-8">
        <label className="mb-2 block text-sm font-medium text-gray-700">{t('common.aiProvider')}</label>
        <ProviderSelector
          providers={providers}
          selected={selectedProvider}
          onSelect={handleProviderSelect}
        />
        {selectedProvider && (
          <div className="mt-4">
            <label htmlFor="grammar-model" className="mb-2 block text-sm font-medium text-gray-700">
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
                id="grammar-model"
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
          <span>{t('grammarEvaluation.evaluating', { count: files.length, provider: selectedProvider })}</span>
        </div>
      )}

      {!loading && (
        <div className="space-y-8">
          {/* File Upload */}
          <section>
            <h2 className="mb-3 text-xl font-semibold text-gray-900">{t('grammarEvaluation.uploadExams')}</h2>
            <p className="mb-4 text-gray-600">
              {t('grammarEvaluation.uploadExamsDescription')}
            </p>
            <FileDropzone
              onFiles={handleFiles}
              disabled={!canUseWorkflow}
              accept={{
                'application/pdf': ['.pdf'],
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
                'application/msword': ['.doc'],
              }}
              multiple
              label={t('grammarEvaluation.dropLabel')}
              description={t('grammarEvaluation.dropDescription')}
            />
            {files.length > 0 && (
              <div className="mt-4 space-y-2">
                <p className="text-sm font-medium text-gray-700">
                  {t('grammarEvaluation.filesSelected', { count: files.length })}
                </p>
                {files.map((file, i) => (
                  <div
                    key={`${file.name}-${i}`}
                    className="flex items-center justify-between rounded-lg border border-gray-200 bg-white px-4 py-2"
                  >
                    <span className="text-sm text-gray-700">{file.name}</span>
                    <button
                      onClick={() => removeFile(i)}
                      className="text-gray-400 hover:text-red-500"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* Evaluation Criteria */}
          <section>
            <h2 className="mb-3 text-xl font-semibold text-gray-900">
              {t('grammarEvaluation.grammarEvaluation')}
            </h2>

            <div className="mb-4 rounded-xl border border-gray-200 bg-white p-5">
              <label className="mb-1 block text-sm text-gray-600">{t('grammarEvaluation.language')}</label>
              <select
                value={correctionLanguage}
                onChange={(e) => setCorrectionLanguage(e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm"
              >
                {LANGUAGES.map((lang) => (
                  <option key={lang.code} value={lang.code}>
                    {lang.label}
                  </option>
                ))}
              </select>
            </div>
          </section>

          {/* Submit */}
          <button
            onClick={handleEvaluate}
            disabled={!canUseWorkflow || files.length === 0}
            className="w-full rounded-xl bg-blue-600 px-6 py-3 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {t('grammarEvaluation.evaluate', { count: files.length, plural: files.length !== 1 ? 's' : '' })}
          </button>
        </div>
      )}
    </div>
  );
}
