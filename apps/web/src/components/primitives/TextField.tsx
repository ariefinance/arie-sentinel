import { useId } from 'react';
import type { InputHTMLAttributes, ReactNode } from 'react';

export interface TextFieldProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, 'id' | 'aria-describedby' | 'aria-invalid'> {
  label: string;
  /** Quiet helper text below the label (e.g. "as management recorded it"). */
  hint?: ReactNode;
  /** Field-level validation error; associated with the input for AT. */
  error?: string;
  required?: boolean;
}

/**
 * Label-above-input field with programmatic label, hint and error association
 * (DESIGN-SYSTEM.md §5; WCAG 2.2 AA). Never uses a placeholder as a label.
 */
export function TextField({
  label,
  hint,
  error,
  required = false,
  className,
  ...rest
}: TextFieldProps) {
  const id = useId();
  const hintId = `${id}-hint`;
  const errorId = `${id}-error`;
  const describedBy = [hint ? hintId : null, error ? errorId : null].filter(Boolean).join(' ');

  return (
    <div className={['field', className].filter(Boolean).join(' ')}>
      <label className="field__label" htmlFor={id}>
        {label}
        {required ? (
          <span className="field__req" aria-hidden="true">
            {' '}
            (required)
          </span>
        ) : (
          <span className="field__opt" aria-hidden="true">
            {' '}
            (optional)
          </span>
        )}
      </label>
      {hint ? (
        <span className="field__hint" id={hintId}>
          {hint}
        </span>
      ) : null}
      <input
        id={id}
        className="field__input"
        required={required}
        aria-required={required}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy || undefined}
        {...rest}
      />
      {error ? (
        <span className="field__error" id={errorId} role="alert">
          {error}
        </span>
      ) : null}
    </div>
  );
}
