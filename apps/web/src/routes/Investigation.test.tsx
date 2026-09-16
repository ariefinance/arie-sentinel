import { QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, expect, test, vi } from 'vitest';
import { createQueryClient } from '../lib/queryClient';
import { Investigation } from './Investigation';

const investigation = {
  investigation_id: 'case-1',
  company_label: 'Example Public Company',
  contact_label: 'Example Public Person',
  case_type: null,
  intake_state: 'SUFFICIENT_FOR_DISCOVERY',
  clarification_reason: null,
  investigation_state: 'COMPLETED',
  company_identity_status: 'AMBIGUOUS',
  company_match_basis: null,
  completeness_state: 'COMPLETE_WITH_LIMITATIONS',
  screening_state: null,
  counterparty: null,
  candidates: [
    {
      candidate_id: 'person-1',
      label_fragment: 'Example Public Person',
      person_evidence_status: null,
      relationship_state: 'UNVERIFIED',
      match_basis: null,
    },
  ],
  entity_candidates: [
    {
      entity_candidate_id: 'entity-1',
      legal_name: 'Example Public Company Ltd',
      jurisdiction: 'gb',
      registry_class: 'opencorporates',
      registry_id: '12345678',
      legal_status: 'Active',
      registered_address: 'Example Street',
      incorporation_date: '2020-01-01',
      lei: null,
      alternative_names: [],
      provider: 'corporate_registry',
      source_ref: 'https://opencorporates.com/companies/gb/12345678',
      retrieved_at: '2026-01-01T00:00:00Z',
      match_basis: 'provider-ranked name search',
    },
  ],
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

afterEach(() => vi.unstubAllGlobals());

test('loads tabs, shows provenance, and resolves a selected candidate', async () => {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.endsWith('/sources'))
      return new Response(
        JSON.stringify([
          {
            source_id: 'source-1',
            source_class: 'corporate_registry',
            title: 'Registry candidate',
            origin_ref: null,
            retrieved_at: '2026-01-01T00:00:00Z',
            captured_by: 'adapter:corporate_registry',
            limitations: 'Candidate only',
            license_class: 'provider-normalized',
          },
        ]),
      );
    if (url.endsWith('/screening') || url.endsWith('/findings')) return new Response('[]');
    if (url.endsWith('/resolve-entity') && init?.method === 'POST')
      return new Response(
        JSON.stringify({
          ...investigation,
          company_identity_status: 'CONFIRMED',
          counterparty: {
            counterparty_id: 'cp-1',
            legal_name: 'Example Public Company Ltd',
            jurisdiction: 'gb',
            registry_class: 'opencorporates',
            registry_id: '12345678',
            status: 'Active',
            identity_key: 'gb:12345678',
          },
        }),
      );
    return new Response(JSON.stringify(investigation));
  });
  vi.stubGlobal('fetch', fetchMock);
  const client = createQueryClient();
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/investigations/case-1']}>
        <Routes>
          <Route path="/investigations/:id" element={<Investigation />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );

  expect(await screen.findByText('Example Public Company')).toBeInTheDocument();
  expect(screen.getByText('Manager finalisation required')).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Final Report →' })).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole('button', { name: 'COMPANY' }));
  expect(await screen.findByText('Example Public Company Ltd')).toBeInTheDocument();
  await userEvent.click(screen.getByRole('button', { name: 'Select entity' }));
  await waitFor(() =>
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/resolve-entity'),
      expect.objectContaining({ method: 'POST' }),
    ),
  );
  await userEvent.click(screen.getByRole('button', { name: 'View sources' }));
  expect(await screen.findByText('Registry candidate')).toBeInTheDocument();
});

test.each([
  {
    screeningState: 'NO_MATERIAL_MATCH',
    completeness: 'COMPLETE_WITH_LIMITATIONS',
    message: 'Screening completed with no material matches.',
  },
  {
    screeningState: null,
    completeness: 'MATERIAL_SOURCE_UNAVAILABLE',
    message: 'Screening was not completed because the provider was unavailable.',
  },
])(
  'shows the correct empty-screening status: $message',
  async ({ screeningState, completeness, message }) => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith('/sources') || url.endsWith('/screening') || url.endsWith('/findings')) {
        return new Response('[]');
      }
      return new Response(
        JSON.stringify({
          ...investigation,
          screening_state: screeningState,
          completeness_state: completeness,
        }),
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

    expect(await screen.findByText('Example Public Company')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'SCREENING' }));
    expect(await screen.findByText(message)).toBeInTheDocument();
  },
);

test('shows no person assessment when no contact was supplied', async () => {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith('/sources') || url.endsWith('/screening') || url.endsWith('/findings')) {
      return new Response('[]');
    }
    return new Response(
      JSON.stringify({
        ...investigation,
        contact_label: '',
        candidates: [],
        company_identity_status: 'CONFIRMED',
      }),
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

  expect(await screen.findByText('No contact supplied')).toBeInTheDocument();
  await userEvent.click(screen.getByRole('button', { name: 'PERSON' }));
  expect(
    await screen.findByText(
      (_content, element) =>
        element?.tagName === 'P' &&
        element.textContent?.includes('Named contact: Not supplied') === true &&
        element.textContent?.includes('Person relationship: Not assessed') === true,
    ),
  ).toBeInTheDocument();
  expect(screen.queryByText('Unverified')).not.toBeInTheDocument();
});

test('labels an unsupported demo company as not searched', async () => {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith('/sources') || url.endsWith('/screening') || url.endsWith('/findings')) {
      return new Response('[]');
    }
    return new Response(
      JSON.stringify({
        ...investigation,
        company_label: 'Unknown Example Holdings',
        contact_label: '',
        candidates: [],
        entity_candidates: [],
        investigation_state: 'SOURCE_UNAVAILABLE',
        company_identity_status: null,
        clarification_reason:
          'Not available in the management-demo dataset. Live registry/provider search is disabled.',
      }),
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

  expect(
    await screen.findByText('Not available in the management-demo dataset'),
  ).toBeInTheDocument();
  expect(screen.getAllByText('Not searched').length).toBeGreaterThan(0);
});
