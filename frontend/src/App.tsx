import { useState, useEffect } from 'react';
import { FileDropzone } from './components/FileDropzone';
import { ProviderSelector } from './components/ProviderSelector';
import { StepIndicator } from './components/StepIndicator';
import { GradingResults } from './components/GradingResults';
import {
  getProviders,
  uploadExamTemplate,
  uploadAnswerKey,
  uploadStudentExams,
  type ProviderConfig,
  type ExamStructure,
  type AnswerKey,
  type GradingResult,
} from './lib/api';
import { Loader2, RotateCcw } from 'lucide-react';

const STEPS = ['Upload Exam Template', 'Upload Answer Key', 'Grade Student Exams'];

function App() {
  const [providers, setProviders] = useState<ProviderConfig[]>([]);
  const [selectedProvider, setSelectedProvider] = useState('');
  const [currentStep, setCurrentStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [examStructure, setExamStructure] = useState<ExamStructure | null>(null);
  const [answerKey, setAnswerKey] = useState<AnswerKey | null>(null);
  const [gradingResults, setGradingResults] = useState<GradingResult[]>([]);

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
    setCurrentStep(0);
    setExamStructure(null);
    setAnswerKey(null);
    setGradingResults([]);
    setError(null);
  };

  const handleExamTemplate = async (files: File[]) => {
    setLoading(true);
    setError(null);
    try {
      const result = await uploadExamTemplate(files[0], selectedProvider);
      setExamStructure(result);
      setCurrentStep(1);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to process exam template');
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
      setError(e instanceof Error ? e.message : 'Failed to process answer key');
    } finally {
      setLoading(false);
    }
  };

  const handleStudentExams = async (files: File[]) => {
    if (!examStructure) return;
    setLoading(true);
    setError(null);
    try {
      const results = await uploadStudentExams(files, examStructure.id, selectedProvider);
      setGradingResults(results);
      setCurrentStep(3);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to grade student exams');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-4xl items-center justify-between px-6 py-4">
          <h1 className="text-2xl font-bold text-gray-900">Exan</h1>
          <button
            onClick={reset}
            className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100"
          >
            <RotateCcw className="h-4 w-4" /> Start Over
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-6 py-8">
        <div className="mb-8">
          <StepIndicator steps={STEPS} currentStep={currentStep} />
        </div>

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
            <span>Processing with {selectedProvider}...</span>
          </div>
        )}

        {!loading && currentStep === 0 && (
          <div className="space-y-4">
            <h2 className="text-xl font-semibold text-gray-900">Step 1: Upload Empty Exam</h2>
            <p className="text-gray-600">
              Upload a PDF or image of the blank exam template. The AI will analyze its structure
              and identify all questions.
            </p>
            <FileDropzone
              onFiles={handleExamTemplate}
              label="Drop exam template here"
              description="PDF or image (PNG, JPG, WebP)"
            />
          </div>
        )}

        {!loading && currentStep === 1 && (
          <div className="space-y-4">
            <h2 className="text-xl font-semibold text-gray-900">Step 2: Upload Answer Key</h2>
            <p className="text-gray-600">
              Upload the exam with the correct answers filled in. This will be used to grade student responses.
            </p>
            {examStructure && (
              <div className="rounded-lg border border-green-200 bg-green-50 p-4 text-sm text-green-800">
                ✓ Detected {examStructure.questions.length} questions in "{examStructure.filename}"
              </div>
            )}
            <FileDropzone
              onFiles={handleAnswerKey}
              label="Drop answer key here"
              description="PDF or image with correct answers"
            />
          </div>
        )}

        {!loading && currentStep === 2 && (
          <div className="space-y-4">
            <h2 className="text-xl font-semibold text-gray-900">Step 3: Upload Student Exams</h2>
            <p className="text-gray-600">
              Upload one or more completed exams from students. Each file will be graded individually.
            </p>
            {answerKey && (
              <div className="rounded-lg border border-green-200 bg-green-50 p-4 text-sm text-green-800">
                ✓ Answer key loaded with {answerKey.answers.length} answers
              </div>
            )}
            <FileDropzone
              onFiles={handleStudentExams}
              multiple
              label="Drop student exams here"
              description="Multiple files supported (PDF or images)"
            />
          </div>
        )}

        {!loading && currentStep === 3 && <GradingResults results={gradingResults} />}
      </main>
    </div>
  );
}

export default App;
