import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { AlertCircle, Info, Upload } from 'lucide-react';
import { useLanguage } from '../lib/i18n';
import { isFileSizeExceeded, MAX_UPLOAD_SIZE_BYTES } from '../lib/file-validation';

interface FileDropzoneProps {
  onFiles: (files: File[]) => void;
  accept?: Record<string, string[]>;
  multiple?: boolean;
  label: string;
  description?: string;
  disabled?: boolean;
  showSizeWarning?: boolean;
}

export function FileDropzone({
  onFiles,
  accept = {
    'application/pdf': ['.pdf'],
    'image/*': ['.png', '.jpg', '.jpeg', '.webp'],
  },
  multiple = false,
  label,
  description,
  disabled = false,
  showSizeWarning = true,
}: FileDropzoneProps) {
  const { t } = useLanguage();
  const [sizeError, setSizeError] = useState<string | null>(null);

  const onDrop = useCallback(
    (accepted: File[]) => {
      setSizeError(null);
      if (accepted.length === 0) return;

      // TODO: This 32 MiB limit check is a temporary safeguard for Cloud Run HTTP/1 limits and must be reworked later
      // (e.g. upload files one-at-a-time, stream via HTTP/2, or implement direct-to-storage signed URLs).
      if (isFileSizeExceeded(accepted, MAX_UPLOAD_SIZE_BYTES)) {
        setSizeError(t('fileDropzone.sizeLimitExceeded'));
        return;
      }

      onFiles(accepted);
    },
    [onFiles, t]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept,
    multiple,
    disabled,
  });

  return (
    <div className="space-y-3">
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors
          ${isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'}
          ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        <input {...getInputProps()} />
        <Upload className="mx-auto mb-3 h-10 w-10 text-gray-400" />
        <p className="text-lg font-medium text-gray-700">{label}</p>
        {description && <p className="mt-1 text-sm text-gray-500">{description}</p>}
        {isDragActive && <p className="mt-2 text-sm text-blue-600">{t('fileDropzone.dropping')}</p>}
      </div>

      {showSizeWarning && (
        <div
          role="status"
          className="flex items-center gap-2 rounded-lg border border-blue-200 bg-blue-50 px-3.5 py-2.5 text-xs text-blue-800"
        >
          <Info className="h-4 w-4 shrink-0 text-blue-600" />
          <span>{t('fileDropzone.maxSizeWarning')}</span>
        </div>
      )}

      {sizeError && (
        <div
          role="alert"
          className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3.5 py-2.5 text-xs text-red-700"
        >
          <AlertCircle className="h-4 w-4 shrink-0 text-red-500" />
          <span>{sizeError}</span>
        </div>
      )}
    </div>
  );
}
