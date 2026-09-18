import { QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, expect, test, vi } from 'vitest';
import { createQueryClient } from '../lib/queryClient';
import { Investigation } from './Investigation';

const investigation = {
  investigation_id: 'case-1',
  company_label: 'Zenith Global Traders Ltd',
  contact_label: 'Robert Vance',
  case_type: 'FICTIONAL_TEST_CASE',
  investigation_context: 'Prospective client',
  intake_state: 'SUFFICIENT_FOR_DISCOVERY',
  clarification_reason: null,
  investigation_state: 'COMPLETED',
  company_identity_status: 'CONFIRMED',
  company_match_basis: 'Analyst selected',
  completeness_state: 'COMPLETE_WITH_LIMITATIONS',
  screening_state: 'NO_MATERIAL_MATCH',
  counterparty: {
    counterparty_id: 'cp-1',
    legal_name: 'Zenith Global Traders Ltd',
    jurisdiction: 'GB',
    registry_class: 'companies_house',
    registry_id: '14750888',
    status: 'Active',
    identity_key: 'gb:14750888',
  },
  candidates: [],
  entity_candidates: [],
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const board = {
  investigation_id: 'case-1',
  investigation_context: 'Prospective client',
  rows: [
    {
      key: 'legal_identity',
      label: 'Legal identity',
      state: 'CONFIRMED',
      detail: 'Zenith Global Traders Ltd',
      action_required: false,
      source_ids: ['s1'],
    },
    {
      key: 'contradictions',
      label: 'Contradictions',
      state: 'CONTRADICTED',
      detail: '2 require review',
      action_required: true,
      source_ids: [],
    },
  ],
};

const graph = {
  investigation_id: 'case-1',
  nodes: [
    { id: 'company:subject', type: 'Company', label: 'Zenith Global Traders Ltd', detail: 'Subject' },
    { id: 'person:robert', type: 'Person', label: 'Robert Vance', detail: '' },
  ],
  edges: [
    {
      source: 'person:robert',
      target: 'company:subject',
      type: 'CLAIMS_TO_REPRESENT',
      basis: 'Supplied contact; relationship not established.',
      state: 'UNVERIFIED',
      source_ids: [],
    },
  ],
};

function mount() {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith('/board')) return new Response(JSON.stringify(board));
    if (url.endsWith('/graph')) return new Response(JSON.stringify(graph));
    if (url.endsWith('/sources') || url.endsWith('/screening') || url.endsWith('/findings'))
      return new Response('[]');
    return new Response(JSON.stringify(investigation));
  });
  vi.stubGlobal('fetch', fetchMock);
  render(
    <QueryClientProvider client={createQueryClient()}>
      <MemoryRouter initialEntries={['/investigations/case-1']}>
        <Routes>
          <Route path="/investigations/:id" element={<Investigation />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

afterEach(() => vi.unstubAllGlobals());

test('the investigation board is the default view and surfaces action-required items', async () => {
  mount();
  // Board is the default tab.
  expect(await screen.findByRole('heading', { name: 'Investigation board' })).toBeInTheDocument();
  expect(await screen.findByText('Legal identity')).toBeInTheDocument();
  expect(screen.getByText('Contradictions')).toBeInTheDocument();
  expect(screen.getByText('2 require review')).toBeInTheDocument();
  // Action is surfaced as text, not colour alone.
  expect(screen.getAllByText('Action required').length).toBeGreaterThan(0);
  // The context is shown in the header.
  expect(screen.getByText('Prospective client')).toBeInTheDocument();
});

test('the relationship map lists provenance-bearing relationships', async () => {
  mount();
  await screen.findByRole('heading', { name: 'Investigation board' });
  await userEvent.click(screen.getByRole('button', { name: 'MAP' }));
  expect(await screen.findByRole('heading', { name: 'Relationship map' })).toBeInTheDocument();
  // The textual relationship list carries the basis (meaning never colour-only).
  expect(
    await screen.findByText(/Supplied contact; relationship not established\./),
  ).toBeInTheDocument();
  expect(screen.getByLabelText('Person: Robert Vance')).toBeInTheDocument();
});
