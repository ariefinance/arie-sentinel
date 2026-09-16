/*
 * API contract types for the ARIE Sentinel backend (FIXED contract).
 * These mirror the response shapes documented for the Stage 1 API and must
 * not drift from it.
 */

export type Role = 'analyst' | 'manager';

export type IntakeState = 'SUFFICIENT_FOR_DISCOVERY' | 'CLARIFICATION_REQUIRED';

export type InvestigationState =
  'NOT_STARTED' | 'RUNNING' | 'PARTIAL_RESULTS' | 'SOURCE_UNAVAILABLE' | 'COMPLETED' | 'FAILED';

export type CompanyIdentityStatus = 'CONFIRMED' | 'AMBIGUOUS' | 'NOT_VERIFIED' | null;

/**
 * Screening state is presented as text and is not exhaustively constrained by
 * the Stage 1 shell; the backend is authoritative. Common canonical values are
 * listed for editor help without rejecting others.
 */
export type ScreeningState =
  | 'NOT_STARTED'
  | 'NO_MATERIAL_MATCH'
  | 'POTENTIAL_MATCH'
  | 'MATCH_REQUIRES_REVIEW'
  | 'CONFIRMED_MATCH'
  | (string & {});

export interface Counterparty {
  counterparty_id: string;
  legal_name: string;
  jurisdiction: string | null;
  registry_class: string | null;
  registry_id: string | null;
  status: string | null;
  identity_key: string | null;
}

export interface PersonCandidate {
  candidate_id: string;
  label_fragment: string;
  person_evidence_status: string | null;
  relationship_state: string | null;
  match_basis: string | null;
}

export interface EntityCandidate {
  entity_candidate_id: string;
  legal_name: string;
  jurisdiction: string | null;
  registry_class: string | null;
  registry_id: string | null;
  legal_status: string | null;
  registered_address: string | null;
  incorporation_date: string | null;
  lei: string | null;
  alternative_names: string[] | null;
  provider: string;
  source_ref: string | null;
  retrieved_at: string;
  match_basis: string | null;
}

export interface InvestigationOut {
  investigation_id: string;
  company_label: string;
  contact_label: string;
  case_type: string | null;
  intake_state: IntakeState;
  clarification_reason: string | null;
  investigation_state: InvestigationState;
  company_identity_status: CompanyIdentityStatus;
  company_match_basis: string | null;
  completeness_state: string | null;
  screening_state: ScreeningState | null;
  counterparty: Counterparty | null;
  candidates: PersonCandidate[];
  entity_candidates: EntityCandidate[];
  created_at: string;
  updated_at: string;
}

export interface WorklistItem {
  investigation_id: string;
  company_label: string;
  contact_label: string;
  case_type: string | null;
  intake_state: IntakeState;
  investigation_state: InvestigationState;
  company_identity_status: CompanyIdentityStatus;
  screening_state: ScreeningState | null;
  needs_action: boolean;
  updated_at: string;
}

export interface AuditEventOut {
  event_id: string;
  actor: string;
  action: string;
  object_type: string;
  target_ref: string | null;
  rationale: string | null;
  created_at: string;
}

export interface HealthOut {
  status: string;
  version: string;
  database: string;
}

export interface CreateInvestigationBody {
  company_label: string;
  contact_label?: string;
}

export interface SourceOut {
  source_id: string;
  source_class: string;
  title: string;
  origin_ref: string | null;
  retrieved_at: string;
  captured_by: string;
  limitations: string | null;
  license_class: string | null;
}

export interface ScreeningResultOut {
  screening_result_id: string;
  subject_label: string;
  list_or_source: string;
  state: ScreeningState;
  match_basis: string | null;
  matched_profile_id: string | null;
  match_score: number | null;
  match_explanation: Record<string, unknown> | null;
  matched_identifiers: Record<string, unknown> | null;
  datasets: string[] | null;
  source_id: string | null;
  analyst_disposition: string | null;
  analyst_rationale: string | null;
  created_at: string;
}

export interface FindingOut {
  finding_id: string;
  finding_type: string;
  severity: string;
  title: string;
  claim_text: string;
  evidence_text: string;
  assessment_text: string;
  action_text: string;
  related_evidence_ids: string[] | null;
  review_status: string;
  created_at: string;
}

/** Derived worklist filters — views over canonical states, never new states. */
export type WorklistFilter =
  | 'all'
  | 'mine'
  | 'needs_action'
  | 'clarification_required'
  | 'identity_ambiguous'
  | 'screening_review'
  | 'completed';
