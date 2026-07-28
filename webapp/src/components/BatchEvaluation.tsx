import { useState, useEffect } from 'react';
import { FileDropzone } from './FileDropzone';
import { ProviderSelector } from './ProviderSelector';
import { BatchResults } from './BatchResults';
import {
  getProviders,
  batchEvaluate,
  type ProviderConfig,
  type EvaluationCriteria,
  type BatchEvaluationResponse,
} from '../lib/api';
import { Loader2, Plus, Trash2, RotateCcw } from 'lucide-react';

interface BatchEvaluationProps {
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

export function BatchEvaluation({ onBack }: BatchEvaluationProps) {
  const [providers, setProviders] = useState<ProviderConfig[]>([]);
  const [selectedProvider, setSelectedProvider] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [files, setFiles] = useState<File[]>([]);
  const [language, setLanguage] = useState('en');
  const [includeGrammar, setIncludeGrammar] = useState(true);
  const [customCriteria, setCustomCriteria] = useState<EvaluationCriteria[]>([]);
  const [results, setResults] = useState<BatchEvaluationResponse | null>(null);

  useEffect(() => {
    getProviders()
      .then((p) => {
        setProviders(p);
        const first = p.find((x) => x.available);
        if (first) setSelectedProvider(first.provider);
      })
      .catch(() => setError('Cannot connect to backend. Is the server running?'));
  }, []);

  const reset = () => {
    setFiles([]);
    setResults(null);
    setError(null);
  };

  const addCriteria = () => {
    setCustomCriteria([
      ...customCriteria,
      { name: '', description: '', zero_description: '', hundred_description: '' },
    ]);
  };

  const updateCriteria = (index: number, field: keyof EvaluationCriteria, value: string) => {
    const updated = [...customCriteria];
    updated[index] = { ...updated[index], [field]: value };
    setCustomCriteria(updated);
  };

  const removeCriteria = (index: number) => {
    setCustomCriteria(customCriteria.filter((_, i) => i !== index));
  };

  const handleFiles = (newFiles: File[]) => {
    setFiles((prev) => [...prev, ...newFiles]);
  };

  const removeFile = (index: number) => {
    setFiles(files.filter((_, i) => i !== index));
  };

  const handleEvaluate = async () => {
    if (files.length === 0) {
      setError('Please upload at least one file');
      return;
    }
    if (!includeGrammar && customCriteria.length === 0) {
      setError('Please select at least one evaluation criteria');
      return;
    }

    const validCriteria = customCriteria.filter(
      (c) => c.name && c.description && c.zero_description && c.hundred_description
    );

    setLoading(true);
    setError(null);
    try {
      const response = await batchEvaluate(
        files,
        selectedProvider,
        language,
        includeGrammar,
        validCriteria
      );
      setResults(response);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Evaluation failed');
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
            ← Back
          </button>
          <button
            onClick={reset}
            className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100"
          >
            <RotateCcw className="h-4 w-4" /> New Evaluation
          </button>
        </div>
        <BatchResults response={results} />
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
          ← Back
        </button>
        <button
          onClick={reset}
          className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100"
        >
          <RotateCcw className="h-4 w-4" /> Reset
        </button>
      </div>

      {/* Provider Selection */}
      <div className="mb-8">
        <label className="mb-2 block text-sm font-medium text-gray-700">AI Provider</label>
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
          <span>Evaluating {files.length} file(s) with {selectedProvider}...</span>
        </div>
      )}

      {!loading && (
        <div className="space-y-8">
          {/* File Upload */}
          <section>
            <h2 className="mb-3 text-xl font-semibold text-gray-900">Upload Exams</h2>
            <p className="mb-4 text-gray-600">
              Upload one or more exams in PDF or Word format. Each file will be evaluated individually.
            </p>
            <FileDropzone
              onFiles={handleFiles}
              accept={{
                'application/pdf': ['.pdf'],
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
                'application/msword': ['.doc'],
              }}
              multiple
              label="Drop exam files here"
              description="PDF or Word documents (.pdf, .docx, .doc)"
            />
            {files.length > 0 && (
              <div className="mt-4 space-y-2">
                <p className="text-sm font-medium text-gray-700">{files.length} file(s) selected:</p>
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
            <h2 className="mb-3 text-xl font-semibold text-gray-900">Evaluation Criteria</h2>

            {/* Grammar */}
            <div className="mb-4 rounded-xl border border-gray-200 bg-white p-5">
              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="grammar"
                  checked={includeGrammar}
                  onChange={(e) => setIncludeGrammar(e.target.checked)}
                  className="h-4 w-4 rounded border-gray-300 text-blue-600"
                />
                <label htmlFor="grammar" className="text-sm font-medium text-gray-900">
                  Grammar Correction
                </label>
                <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs text-blue-700">
                  Default
                </span>
              </div>
              {includeGrammar && (
                <div className="mt-3 ml-7">
                  <label className="mb-1 block text-sm text-gray-600">Language</label>
                  <select
                    value={language}
                    onChange={(e) => setLanguage(e.target.value)}
                    className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm"
                  >
                    {LANGUAGES.map((lang) => (
                      <option key={lang.code} value={lang.code}>
                        {lang.label}
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>

            {/* Custom Criteria */}
            <div className="space-y-4">
              {customCriteria.map((criteria, index) => (
                <div
                  key={index}
                  className="rounded-xl border border-gray-200 bg-white p-5"
                >
                  <div className="mb-3 flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-700">
                      Custom Criteria #{index + 1}
                    </span>
                    <button
                      onClick={() => removeCriteria(index)}
                      className="text-gray-400 hover:text-red-500"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                  <div className="space-y-3">
                    <input
                      type="text"
                      placeholder="Criteria name (e.g., Argument Quality)"
                      value={criteria.name}
                      onChange={(e) => updateCriteria(index, 'name', e.target.value)}
                      className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                    />
                    <textarea
                      placeholder="Description — what should the AI evaluate?"
                      value={criteria.description}
                      onChange={(e) => updateCriteria(index, 'description', e.target.value)}
                      rows={2}
                      className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                    />
                    <div className="grid grid-cols-2 gap-3">
                      <textarea
                        placeholder="What does 0% look like?"
                        value={criteria.zero_description}
                        onChange={(e) => updateCriteria(index, 'zero_description', e.target.value)}
                        rows={2}
                        className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                      />
                      <textarea
                        placeholder="What does 100% look like?"
                        value={criteria.hundred_description}
                        onChange={(e) =>
                          updateCriteria(index, 'hundred_description', e.target.value)
                        }
                        rows={2}
                        className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                      />
                    </div>
                  </div>
                </div>
              ))}

              <button
                onClick={addCriteria}
                className="flex w-full items-center justify-center gap-2 rounded-xl border-2 border-dashed border-gray-300 px-4 py-3 text-sm font-medium text-gray-600 hover:border-gray-400 hover:text-gray-700"
              >
                <Plus className="h-4 w-4" /> Add Custom Criteria
              </button>
            </div>
          </section>

          {/* Submit */}
          <button
            onClick={handleEvaluate}
            disabled={files.length === 0 || (!includeGrammar && customCriteria.length === 0)}
            className="w-full rounded-xl bg-blue-600 px-6 py-3 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Evaluate {files.length} File{files.length !== 1 ? 's' : ''}
          </button>
        </div>
      )}
    </div>
  );
}
