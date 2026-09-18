import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
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

test('board and map show an explicit unavailable state on API error, not empty results', async () => {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith('/board')) return new Response('{"detail":"boom"}', { status: 500 });
    if (url.endsWith('/graph')) return new Response('{"detail":"boom"}', { status: 500 });
    if (url.endsWith('/sources') || url.endsWith('/screening') || url.endsWith('/findings'))
      return new Response('[]');
    return new Response(JSON.stringify(investigation));
  });
  vi.stubGlobal('fetch', fetchMock);
  const noRetry = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={noRetry}>
      <MemoryRouter initialEntries={['/investigations/case-1']}>
        <Routes>
          <Route path="/investigations/:id" element={<Investigation />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
  expect(await screen.findByText('Investigation Board unavailable')).toBeInTheDocument();
  await userEvent.click(screen.getByRole('button', { name: 'MAP' }));
  expect(await screen.findByText('Relationship data unavailable')).toBeInTheDocument();
});

test('a board row opens only its own sources (row-specific drill-down)', async () => {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith('/board')) return new Response(JSON.stringify(board));
    if (url.endsWith('/graph')) return new Response(JSON.stringify(graph));
    if (url.endsWith('/screening') || url.endsWith('/findings')) return new Response('[]');
    if (url.endsWith('/sources'))
      return new Response(
        JSON.stringify([
          {
            source_id: 's1',
            source_class: 'corporate_registry',
            title: 'Registry candidate: Zenith',
            origin_ref: null,
            retrieved_at: '2026-01-01T00:00:00Z',
            captured_by: 'fixture:corporate_registry',
            limitations: 'candidate',
            license_class: 'fixture-non-live',
          },
          {
            source_id: 's2',
            source_class: 'web_public',
            title: 'Unrelated web source',
            origin_ref: null,
            retrieved_at: '2026-01-01T00:00:00Z',
            captured_by: 'adapter:web_search:discovery',
            limitations: 'discovery',
            license_class: 'linked-public-source',
          },
        ]),
      );
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
  await screen.findByRole('heading', { name: 'Investigation board' });
  // Legal identity row carries source s1 only.
  await userEvent.click(screen.getByRole('button', { name: /source.* for Legal identity/i }));
  expect(await screen.findByText('Registry candidate: Zenith')).toBeInTheDocument();
  expect(screen.queryByText('Unrelated web source')).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Show all investigation sources' })).toBeInTheDocument();
});

test('the board refreshes as the investigation progresses', async () => {
  // `done` flips only on the SECOND investigation read (the poll), so the initial
  // board render is deterministically "running" regardless of fetch ordering.
  let invCalls = 0;
  let done = false;
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith('/board'))
      return new Response(
        JSON.stringify({
          investigation_id: 'case-1',
          investigation_context: null,
          rows: [
            {
              key: 'legal_identity',
              label: 'Legal identity',
              state: done ? 'CONFIRMED' : 'UNVERIFIED',
              detail: done ? 'Zenith Global Traders Ltd' : 'Not yet established',
              action_required: false,
              source_ids: [],
            },
          ],
        }),
      );
    if (url.endsWith('/graph')) return new Response(JSON.stringify(graph));
    if (url.endsWith('/sources') || url.endsWith('/screening') || url.endsWith('/findings'))
      return new Response('[]');
    invCalls += 1;
    if (invCalls >= 2) done = true; // the worker completes by the first poll
    return new Response(
      JSON.stringify({ ...investigation, investigation_state: done ? 'COMPLETED' : 'RUNNING' }),
    );
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
  // Initial (running) board, then the polled investigation advances and the board is
  // invalidated + refetched, showing the completed evidence — no manual refresh.
  expect(await screen.findByText('Not yet established')).toBeInTheDocument();
  // After the investigation advances, the board is refetched and the running-state
  // detail is replaced — no manual refresh.
  await waitFor(() => expect(screen.queryByText('Not yet established')).not.toBeInTheDocument(), {
    timeout: 4500,
  });
});
