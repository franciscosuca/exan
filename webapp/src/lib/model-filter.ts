import type { ProviderModel } from './api';

const MIN_MAJOR_VERSION: Record<string, number> = {
  gemma: 4,
  gemini: 3,
};

const VERSIONED_MODEL_ID = /^(gemma|gemini)-(\d+)(?:\.\d+)*(?:-|$)/;
const EXCLUDED_DISPLAY_NAME = /nano\s*banana|lyria|deep\s*research/;

function isEligibleModelId(rawId: string): boolean {
  const id = rawId.trim().toLowerCase().replace(/^models\//, '');
  const match = VERSIONED_MODEL_ID.exec(id);
  if (!match) return false;
  return Number(match[2]) >= MIN_MAJOR_VERSION[match[1]];
}

/**
 * Keep only Gemma 4+ and Gemini 3+ models with a canonical versioned ID,
 * preserving the order returned by the API.
 */
export function filterGoogleModels(models: ProviderModel[]): ProviderModel[] {
  return models.filter((model) => {
    if (EXCLUDED_DISPLAY_NAME.test((model.display_name ?? '').toLowerCase())) return false;
    return isEligibleModelId(model.id ?? '') || isEligibleModelId(model.name ?? '');
  });
}
