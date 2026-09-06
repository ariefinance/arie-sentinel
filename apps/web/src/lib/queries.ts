import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from './api';
import type { CreateInvestigationBody, WorklistFilter } from './types';

export const queryKeys = {
  health: ['health'] as const,
  worklist: (filter: WorklistFilter) => ['worklist', filter] as const,
  investigation: (id: string) => ['investigation', id] as const,
  audit: (id: string) => ['investigation', id, 'audit'] as const,
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
