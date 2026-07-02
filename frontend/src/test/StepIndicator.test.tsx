import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { StepIndicator } from '../components/StepIndicator';

const STEPS = ['Step A', 'Step B', 'Step C'];

describe('StepIndicator', () => {
  it('renders all step labels', () => {
    render(<StepIndicator steps={STEPS} currentStep={0} />);
    expect(screen.getByText('Step A')).toBeInTheDocument();
    expect(screen.getByText('Step B')).toBeInTheDocument();
    expect(screen.getByText('Step C')).toBeInTheDocument();
  });

  it('shows current step number', () => {
    render(<StepIndicator steps={STEPS} currentStep={1} />);
    // Step 1 (index 0) should be completed (checkmark), step 2 is current
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('marks completed steps with checkmark', () => {
    const { container } = render(<StepIndicator steps={STEPS} currentStep={2} />);
    // Steps 0 and 1 are completed, so they should have green background
    const greenCircles = container.querySelectorAll('.bg-green-600');
    expect(greenCircles.length).toBe(2);
  });
});
