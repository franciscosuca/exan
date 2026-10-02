import { render, screen } from '@testing-library/react';
import { describe, it, expect, beforeEach } from 'vitest';
import { SelectionRequiredNotice } from '../components/SelectionRequiredNotice';
import { LanguageProvider, LANGUAGE_STORAGE_KEY } from '../lib/i18n';

function renderNotice(hasProvider: boolean, hasModel: boolean) {
  return render(
    <LanguageProvider>
      <SelectionRequiredNotice hasProvider={hasProvider} hasModel={hasModel} />
    </LanguageProvider>
  );
}

describe('SelectionRequiredNotice', () => {
  beforeEach(() => {
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, 'en');
  });

  it('asks for a provider when none is selected', () => {
    renderNotice(false, false);
    expect(screen.getByRole('status')).toHaveTextContent(/Choose an AI provider above/);
  });

  it('asks for a model when only the provider is selected', () => {
    renderNotice(true, false);
    expect(screen.getByRole('status')).toHaveTextContent(/Pick an AI model above/);
  });

  it('renders nothing once both are selected', () => {
    renderNotice(true, true);
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });
});
