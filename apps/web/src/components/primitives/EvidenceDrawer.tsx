/*
 * EvidenceDrawer — an in-context slide-over panel (UI-UX-SPEC.md §8a).
 *
 * It opens over the current context and closes back to it. For Stage 1 the
 * content is placeholder, but the interaction contract is real:
 *  - role="dialog", aria-modal, labelled by its heading;
 *  - focus moves into the drawer on open and is TRAPPED while open;
 *  - Escape or the Close button dismisses it;
 *  - focus returns to the element that invoked it on close.
 */

import { useEffect, useRef } from 'react';
import type { ReactNode } from 'react';
import { Button } from './Button';

export interface EvidenceDrawerProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children?: ReactNode;
  footer?: ReactNode;
}

const FOCUSABLE =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

export function EvidenceDrawer({ open, onClose, title, children, footer }: EvidenceDrawerProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const previouslyFocused = useRef<HTMLElement | null>(null);

  // Move focus into the drawer on open; restore it on close.
  useEffect(() => {
    if (!open) return;
    previouslyFocused.current = document.activeElement as HTMLElement | null;
    closeButtonRef.current?.focus();
    return () => {
      previouslyFocused.current?.focus?.();
    };
  }, [open]);

  // Escape to dismiss + a focus trap that keeps Tab within the panel.
  useEffect(() => {
    if (!open) return;

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        event.stopPropagation();
        onClose();
        return;
      }
      if (event.key !== 'Tab') return;

      const panel = panelRef.current;
      if (!panel) return;
      const focusable = Array.from(panel.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
        (el) => el.offsetParent !== null || el === document.activeElement,
      );
      if (focusable.length === 0) {
        event.preventDefault();
        return;
      }
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      const active = document.activeElement;

      if (event.shiftKey && active === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && active === last) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener('keydown', onKeyDown, true);
    return () => document.removeEventListener('keydown', onKeyDown, true);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="drawer-layer">
      {/* Backdrop: clicking it closes, but it is not a keyboard target. */}
      <div className="drawer-backdrop" onClick={onClose} aria-hidden="true" />
      <div
        className="drawer-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="evidence-drawer-title"
        ref={panelRef}
      >
        <header className="drawer-panel__header">
          <h2 className="drawer-panel__title" id="evidence-drawer-title">
            {title}
          </h2>
          <Button ref={closeButtonRef} variant="ghost" onClick={onClose} aria-label="Close evidence">
            Close
          </Button>
        </header>
        <div className="drawer-panel__body">{children}</div>
        {footer ? <footer className="drawer-panel__footer">{footer}</footer> : null}
      </div>
    </div>
  );
}
