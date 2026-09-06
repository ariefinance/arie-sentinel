/*
 * Shared state presentations (DESIGN-SYSTEM.md §8, SCREEN-STATES.md §8):
 * skeletons for loading, explanatory empty states, and recoverable error
 * blocks. No spinners-without-context; no dead ends.
 */

import type { ReactNode } from 'react';
import { Button } from './Button';

export interface LoadingStateProps {
  label: string;
  /** Number of skeleton rows to show. */
  rows?: number;
}

export function LoadingState({ label, rows = 3 }: LoadingStateProps) {
  return (
    <div className="state-block" aria-live="polite" aria-busy="true">
      <p className="state-block__label">{label}</p>
      <div className="skeleton-list">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="skeleton-row" aria-hidden="true" />
        ))}
      </div>
    </div>
  );
}

export interface EmptyStateProps {
  title: string;
  description?: ReactNode;
  action?: ReactNode;
}

export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <div className="state-block state-block--empty">
      <p className="state-block__title">{title}</p>
      {description ? <p className="state-block__desc">{description}</p> : null}
      {action ? <div className="state-block__action">{action}</div> : null}
    </div>
  );
}

export interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
}

export function ErrorState({ title = 'Could not load', message, onRetry }: ErrorStateProps) {
  return (
    <div className="state-block state-block--error" role="alert">
      <p className="state-block__title">{title}</p>
      <p className="state-block__desc">{message}</p>
      {onRetry ? (
        <div className="state-block__action">
          <Button variant="secondary" onClick={onRetry}>
            Retry
          </Button>
        </div>
      ) : null}
    </div>
  );
}
