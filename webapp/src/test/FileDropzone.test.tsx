import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { FileDropzone } from '../components/FileDropzone';
import { LanguageProvider, LANGUAGE_STORAGE_KEY } from '../lib/i18n';

function renderFileDropzone(props: Partial<React.ComponentProps<typeof FileDropzone>> = {}) {
  const defaultProps = {
    onFiles: vi.fn(),
    label: 'Upload test files',
    description: 'PDF or image files',
    ...props,
  };

  const utils = render(
    <LanguageProvider>
      <FileDropzone {...defaultProps} />
    </LanguageProvider>
  );

  return { ...utils, props: defaultProps };
}

describe('FileDropzone', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, 'en');
  });

  it('renders label and description', () => {
    renderFileDropzone({ label: 'Drop files here', description: 'Supports PDF only' });

    expect(screen.getByText('Drop files here')).toBeInTheDocument();
    expect(screen.getByText('Supports PDF only')).toBeInTheDocument();
  });

  it('renders the 32 MiB warning info box by default', () => {
    renderFileDropzone();

    const infoBox = screen.getByRole('status');
    expect(infoBox).toBeInTheDocument();
    expect(infoBox).toHaveTextContent(/cannot be bigger than 32 MiB/i);
  });

  it('can hide the size warning info box if configured', () => {
    renderFileDropzone({ showSizeWarning: false });

    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });

  it('calls onFiles when valid files under 32 MiB are uploaded', async () => {
    const user = userEvent.setup();
    const onFiles = vi.fn();
    const { container } = renderFileDropzone({ onFiles });

    const file = new File(['content'], 'test.pdf', { type: 'application/pdf' });
    const input = container.querySelector('input[type="file"]') as HTMLInputElement;

    await user.upload(input, file);

    await waitFor(() => {
      expect(onFiles).toHaveBeenCalledWith([file]);
    });
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('displays an error alert and does not call onFiles when uploaded files exceed 32 MiB', async () => {
    const user = userEvent.setup();
    const onFiles = vi.fn();
    const { container } = renderFileDropzone({ onFiles });

    const largeFile = new File([''], 'huge.pdf', { type: 'application/pdf' });
    Object.defineProperty(largeFile, 'size', { value: 34 * 1024 * 1024, configurable: true });

    const input = container.querySelector('input[type="file"]') as HTMLInputElement;
    await user.upload(input, largeFile);

    await waitFor(() => {
      const alert = screen.getByRole('alert');
      expect(alert).toBeInTheDocument();
      expect(alert).toHaveTextContent(/exceed the maximum size limit of 32 MiB/i);
    });

    expect(onFiles).not.toHaveBeenCalled();
  });
});
