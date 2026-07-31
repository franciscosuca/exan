import { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload } from 'lucide-react';
import { useLanguage } from '../lib/i18n';

interface FileDropzoneProps {
  onFiles: (files: File[]) => void;
  accept?: Record<string, string[]>;
  multiple?: boolean;
  label: string;
  description?: string;
  disabled?: boolean;
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
}: FileDropzoneProps) {
  const onDrop = useCallback(
    (accepted: File[]) => {
      if (accepted.length > 0) onFiles(accepted);
    },
    [onFiles]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept,
    multiple,
    disabled,
  });

  const { t } = useLanguage();

  return (
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
  );
}
