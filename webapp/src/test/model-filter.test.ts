import { describe, it, expect } from 'vitest';
import { filterGoogleModels } from '../lib/model-filter';
import type { ProviderModel } from '../lib/api';

function model(id: string, display_name = id): ProviderModel {
  return { id, name: id, display_name, supported_actions: ['generateContent'] };
}

const ids = (models: ProviderModel[]) => models.map((m) => m.id);

describe('filterGoogleModels', () => {
  it('keeps eligible Gemma 4+ and Gemini 3+ versions', () => {
    const input = [
      model('gemini-3-pro'),
      model('gemini-3.1-flash'),
      model('gemini-4-ultra'),
      model('gemma-4-27b-it'),
      model('gemma-5'),
    ];
    expect(ids(filterGoogleModels(input))).toEqual(ids(input));
  });

  it('hides older versions', () => {
    const input = [
      model('gemini-2.5-flash'),
      model('gemini-2.0-pro'),
      model('gemini-1.5-pro'),
      model('gemma-3-27b-it'),
      model('gemma-3n-e4b-it'),
    ];
    expect(filterGoogleModels(input)).toEqual([]);
  });

  it('hides versionless aliases and unrelated models', () => {
    const input = [
      model('gemini-flash-latest'),
      model('gemini-pro-latest'),
      model('gemini-embedding-001'),
      model('lyria-realtime-exp', 'Lyria RealTime'),
      model('deep-research-pro-preview', 'Deep Research Pro'),
      model('gemini-2.5-flash-image', 'Nano Banana'),
      model('gemini-3-pro-image-preview', 'Nano Banana Pro'),
    ];
    expect(filterGoogleModels(input)).toEqual([]);
  });

  it('keeps aliases when the API provides a canonical eligible ID', () => {
    const alias: ProviderModel = {
      id: 'gemini-flash-latest',
      name: 'models/gemini-3-flash',
      display_name: 'Gemini Flash Latest',
      supported_actions: [],
    };
    expect(filterGoogleModels([alias])).toEqual([alias]);
  });

  it('compares case-insensitively', () => {
    const input = [model('Gemini-3-Pro'), model('GEMMA-4-12B'), model('GEMINI-2.5-FLASH')];
    expect(ids(filterGoogleModels(input))).toEqual(['Gemini-3-Pro', 'GEMMA-4-12B']);
  });

  it('keeps preview and suffix variants and preserves order', () => {
    const input = [
      model('gemini-3-pro-preview-06-05'),
      model('gemini-2.5-pro-preview'),
      model('models/gemma-4-1b-it'),
      model('gemini-3.1-flash-lite-preview'),
      model('gemini-3-flash-001'),
    ];
    expect(ids(filterGoogleModels(input))).toEqual([
      'gemini-3-pro-preview-06-05',
      'models/gemma-4-1b-it',
      'gemini-3.1-flash-lite-preview',
      'gemini-3-flash-001',
    ]);
  });

  it('returns an empty list when nothing passes', () => {
    expect(filterGoogleModels([model('gemini-2.5-flash')])).toEqual([]);
    expect(filterGoogleModels([])).toEqual([]);
  });
});
