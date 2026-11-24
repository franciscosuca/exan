import { describe, expect, it } from 'vitest';
import {
  calculateTotalFileSize,
  formatFileSize,
  isFileSizeExceeded,
  MAX_UPLOAD_SIZE_BYTES,
  MAX_UPLOAD_SIZE_MIB,
} from './file-validation';

describe('file-validation', () => {
  it('defines 32 MiB as the upload limit', () => {
    expect(MAX_UPLOAD_SIZE_MIB).toBe(32);
    expect(MAX_UPLOAD_SIZE_BYTES).toBe(32 * 1024 * 1024);
    expect(MAX_UPLOAD_SIZE_BYTES).toBe(33554432);
  });

  describe('calculateTotalFileSize', () => {
    it('returns 0 for empty, null, or undefined input', () => {
      expect(calculateTotalFileSize(null)).toBe(0);
      expect(calculateTotalFileSize(undefined)).toBe(0);
      expect(calculateTotalFileSize([])).toBe(0);
    });

    it('calculates size for a single file', () => {
      const file = new File(['hello world'], 'test.txt', { type: 'text/plain' });
      expect(calculateTotalFileSize(file)).toBe(file.size);
    });

    it('sums sizes for multiple files', () => {
      const file1 = new File(['a'.repeat(100)], 'file1.txt');
      const file2 = new File(['b'.repeat(200)], 'file2.txt');
      const file3 = new File(['c'.repeat(300)], 'file3.txt');
      expect(calculateTotalFileSize([file1, file2, file3])).toBe(600);
    });
  });

  describe('isFileSizeExceeded', () => {
    it('returns false when total size is below limit', () => {
      const smallFile = new File(['hello'], 'small.txt');
      expect(isFileSizeExceeded(smallFile)).toBe(false);
      expect(isFileSizeExceeded([smallFile])).toBe(false);
      expect(isFileSizeExceeded(1024)).toBe(false);
    });

    it('returns false when total size is exactly 32 MiB', () => {
      expect(isFileSizeExceeded(MAX_UPLOAD_SIZE_BYTES)).toBe(false);
    });

    it('returns true when total size exceeds 32 MiB', () => {
      expect(isFileSizeExceeded(MAX_UPLOAD_SIZE_BYTES + 1)).toBe(true);
    });

    it('returns true when array of files exceeds 32 MiB', () => {
      // Mock large files using Object.defineProperty to avoid huge memory allocations in test
      const bigFile1 = { size: 20 * 1024 * 1024, name: 'big1.pdf' } as unknown as File;
      const bigFile2 = { size: 15 * 1024 * 1024, name: 'big2.pdf' } as unknown as File;
      expect(isFileSizeExceeded([bigFile1, bigFile2])).toBe(true);
    });

    it('supports custom max size in bytes', () => {
      expect(isFileSizeExceeded(500, 400)).toBe(true);
      expect(isFileSizeExceeded(300, 400)).toBe(false);
    });

    it('handles null and undefined gracefully', () => {
      expect(isFileSizeExceeded(null)).toBe(false);
      expect(isFileSizeExceeded(undefined)).toBe(false);
    });
  });

  describe('formatFileSize', () => {
    it('formats 0 bytes', () => {
      expect(formatFileSize(0)).toBe('0 B');
    });

    it('formats bytes, KiB, MiB, GiB', () => {
      expect(formatFileSize(512)).toBe('512 B');
      expect(formatFileSize(1024)).toBe('1 KiB');
      expect(formatFileSize(1.5 * 1024 * 1024)).toBe('1.5 MiB');
      expect(formatFileSize(32 * 1024 * 1024)).toBe('32 MiB');
    });
  });
});
