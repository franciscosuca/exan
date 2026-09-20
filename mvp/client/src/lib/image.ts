// Allowed raster image MIME types. SVG is intentionally excluded because it can embed
// scripts, and images captured here are eventually rendered directly in an <img>.
const ALLOWED_MIME_TYPES = new Set(['image/png', 'image/jpeg', 'image/webp', 'image/gif']);

const DATA_URL_PATTERN = /^data:(image\/[a-z+.-]+);base64,([A-Za-z0-9+/]+=*)$/;

function hasSignature(bytes: Uint8Array, signature: number[], offset = 0): boolean {
  if (bytes.length < offset + signature.length) return false;
  return signature.every((byte, index) => bytes[offset + index] === byte);
}

function matchesDeclaredType(bytes: Uint8Array, mimeType: string): boolean {
  switch (mimeType) {
    case 'image/png':
      return hasSignature(bytes, [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
    case 'image/jpeg':
      return hasSignature(bytes, [0xff, 0xd8, 0xff]);
    case 'image/gif':
      return hasSignature(bytes, [0x47, 0x49, 0x46, 0x38]);
    case 'image/webp':
      return hasSignature(bytes, [0x52, 0x49, 0x46, 0x46]) && hasSignature(bytes, [0x57, 0x45, 0x42, 0x50], 8);
    default:
      return false;
  }
}

/**
 * Converts a `data:` URL received from an untrusted source into a same-origin
 * `blob:` object URL, but only after confirming both the declared MIME type and the
 * binary file signature match one of the allowed raster image formats. Returns
 * `null` for anything else (including SVGs, which can embed scripts).
 */
export function toSafeImageObjectUrl(dataUrl: string): string | null {
  const match = DATA_URL_PATTERN.exec(dataUrl);
  if (!match) return null;

  const [, mimeType, base64] = match;
  if (!ALLOWED_MIME_TYPES.has(mimeType)) return null;

  let bytes: Uint8Array<ArrayBuffer>;
  try {
    const binary = atob(base64);
    bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i += 1) {
      bytes[i] = binary.charCodeAt(i);
    }
  } catch {
    return null;
  }

  if (!matchesDeclaredType(bytes, mimeType)) return null;

  const blob = new Blob([bytes], { type: mimeType });
  return URL.createObjectURL(blob);
}
