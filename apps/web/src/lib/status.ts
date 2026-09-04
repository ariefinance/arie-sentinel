/*
 * Maps canonical API state values to a StatusPill tone. The pill label is
 * always the canonical state word itself (state is text-first, per
 * DESIGN-SYSTEM.md §4 / §8) — colour is only reinforcement and every tone also
 * carries a distinct shape glyph so status survives greyscale.
 */

import type { PillTone } from '../components/primitives/StatusPill';
import type {
  CompanyIdentityStatus,
  IntakeState,
  InvestigationState,
  ScreeningState,
} from './types';

export function intakeTone(state: IntakeState): PillTone {
  return state === 'SUFFICIENT_FOR_DISCOVERY' ? 'info' : 'caution';
}

export function investigationTone(state: InvestigationState): PillTone {
  switch (state) {
    case 'COMPLETED':
      return 'positive';
    case 'RUNNING':
    case 'PARTIAL_RESULTS':
      return 'info';
    case 'SOURCE_UNAVAILABLE':
      return 'caution';
    case 'FAILED':
      return 'attention';
    case 'NOT_STARTED':
    default:
      return 'neutral';
  }
}

export function identityTone(status: CompanyIdentityStatus): PillTone {
  switch (status) {
    case 'CONFIRMED':
      return 'positive';
    case 'AMBIGUOUS':
    case 'NOT_VERIFIED':
      return 'caution';
    default:
      return 'neutral';
  }
}

export function screeningTone(state: ScreeningState | null): PillTone {
  switch (state) {
    case 'CONFIRMED_MATCH':
    case 'MATCH_REQUIRES_REVIEW':
    case 'POTENTIAL_MATCH':
      return 'attention';
    case 'NO_MATERIAL_MATCH':
      return 'info';
    case 'NOT_STARTED':
    case null:
    case undefined:
      return 'neutral';
    default:
      return 'info';
  }
}

/** The label shown for a screening dimension when the backend sends null. */
export const SCREENING_NOT_RUN = 'NOT_RUN';
