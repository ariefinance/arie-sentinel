import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from './api';
import type { CreateInvestigationBody, WorklistFilter } from './types';

export const queryKeys = {
  health: ['health'] as const,
  worklist: (filter: WorklistFilter) => ['worklist', filter] as const,
  investigation: (id: string) => ['investigation', id] as const,
  audit: (id: string) => ['investigation', id, 'audit'] as const,
  sources: (id: string) => ['investigation', id, 'sources'] as const,
  screening: (id: string) => ['investigation', id, 'screening'] as const,
  findings: (id: string) => ['investigation', id, 'findings'] as const,
};

export function useHealth() {
  return useQuery({
    queryKey: queryKeys.health,
    queryFn: ({ signal }) => api.health(signal),
    staleTime: 60_000,
  });
}

export function useWorklist(filter: WorklistFilter) {
  return useQuery({
    queryKey: queryKeys.worklist(filter),
    queryFn: ({ signal }) => api.getWorklist(filter, signal),
  });
}

// Investigation state advances asynchronously (a background worker runs
// discovery). While the state is non-terminal, poll so the UI reflects
// RUNNING -> COMPLETED without a manual refresh.
const NON_TERMINAL = new Set(['NOT_STARTED', 'RUNNING', 'PARTIAL_RESULTS']);

export function useInvestigation(id: string) {
  return useQuery({
    queryKey: queryKeys.investigation(id),
    queryFn: ({ signal }) => api.getInvestigation(id, signal),
    enabled: id.length > 0,
    refetchInterval: (query) => {
      const state = query.state.data?.investigation_state;
      return state && NON_TERMINAL.has(state) ? 2000 : false;
    },
  });
}

export function useAudit(id: string) {
  return useQuery({
    queryKey: queryKeys.audit(id),
    queryFn: ({ signal }) => api.getAudit(id, signal),
    enabled: id.length > 0,
  });
}

export function useSources(id: string) {
  return useQuery({ queryKey: queryKeys.sources(id), queryFn: ({ signal }) => api.getSources(id, signal), enabled: id.length > 0 });
}

export function useScreening(id: string) {
  return useQuery({ queryKey: queryKeys.screening(id), queryFn: ({ signal }) => api.getScreening(id, signal), enabled: id.length > 0 });
}

export function useFindings(id: string) {
  return useQuery({ queryKey: queryKeys.findings(id), queryFn: ({ signal }) => api.getFindings(id, signal), enabled: id.length > 0 });
}

export function useResolveEntity(id: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ candidateId, rationale }: { candidateId: string; rationale: string }) => api.resolveEntity(id, candidateId, rationale),
    onSuccess: (data) => {
      client.setQueryData(queryKeys.investigation(id), data);
      void client.invalidateQueries({ queryKey: ['investigation', id] });
    },
  });
}

export function useReviewScreening(id: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ resultId, disposition, rationale }: { resultId: string; disposition: string; rationale: string }) => api.reviewScreening(resultId, disposition, rationale),
    onSuccess: () => void client.invalidateQueries({ queryKey: queryKeys.screening(id) }),
  });
}

export function useReviewFinding(id: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ findingId, disposition, rationale }: { findingId: string; disposition: string; rationale: string }) => api.reviewFinding(findingId, disposition, rationale),
    onSuccess: () => void client.invalidateQueries({ queryKey: queryKeys.findings(id) }),
  });
}

export function useCreateInvestigation() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateInvestigationBody) => api.createInvestigation(body),
    onSuccess: (data) => {
      client.setQueryData(queryKeys.investigation(data.investigation_id), data);
      void client.invalidateQueries({ queryKey: ['worklist'] });
    },
  });
}
