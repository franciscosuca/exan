/**
 * Upload size limits and validation.
 *
 * Cloud Run default HTTP/1 request limit is 32 MiB (33,554,432 bytes).
 *
 * TODO: This 32 MiB client-side check is a temporary limit and must be reworked later
 * (e.g. by uploading files one by one, streaming via HTTP/2, or implementing direct-to-storage signed URLs).
 */

export const MAX_UPLOAD_SIZE_BYTES = 32 * 1024 * 1024; // 32 MiB = 33,554,432 bytes
export const MAX_UPLOAD_SIZE_MIB = 32;

/**
 * Calculates the total size in bytes of a single file or a list of files.
 */
export function calculateTotalFileSize(
  files: File | File[] | readonly File[] | null | undefined
): number {
  if (!files) return 0;
  if (Array.isArray(files)) {
    return files.reduce((total: number, file: File) => total + file.size, 0);
  }
  if (files instanceof File) {
    return files.size;
  }
  return 0;
}

/**
 * Checks whether the total size of uploaded file(s) exceeds the maximum allowed limit (32 MiB).
 *
 * TODO: This calculation must be reworked later when moving to chunked or direct-to-storage uploads.
 *
 * @param files A single file, an array of files, or a pre-calculated total size in bytes.
 * @param maxSizeBytes The maximum allowed size in bytes (defaults to 32 MiB).
 * @returns true if the total file size exceeds the limit, false otherwise.
 */
export function isFileSizeExceeded(
  files: File | File[] | readonly File[] | number | null | undefined,
  maxSizeBytes: number = MAX_UPLOAD_SIZE_BYTES
): boolean {
  if (files == null) return false;
  const totalBytes = typeof files === 'number' ? files : calculateTotalFileSize(files);
  return totalBytes > maxSizeBytes;
}

/**
 * Formats bytes into a human-readable string (e.g., "12.4 MiB" or "500 KiB").
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KiB', 'MiB', 'GiB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  const value = bytes / Math.pow(k, i);
  return `${parseFloat(value.toFixed(2))} ${sizes[i]}`;
}
