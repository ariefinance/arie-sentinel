import { QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, expect, test, vi } from 'vitest';
import { createQueryClient } from '../lib/queryClient';
import { Investigate } from './Investigate';

afterEach(() => vi.unstubAllGlobals());

test('starts a company-only public validation investigation', async () => {
  const fetchMock = vi.fn(
    async (_input: RequestInfo | URL, init?: RequestInit) =>
      new Response(
        JSON.stringify({
          investigation_id: 'arie-case',
          company_label: 'ARIE Finance',
          contact_label: '',
          case_type: 'PUBLIC_VALIDATION_CASE',
          intake_state: 'SUFFICIENT_FOR_DISCOVERY',
          clarification_reason: null,
          investigation_state: 'NOT_STARTED',
          company_identity_status: null,
          company_match_basis: null,
          completeness_state: null,
          screening_state: null,
          counterparty: null,
          candidates: [],
          entity_candidates: [],
          created_at: '2026-09-16T00:00:00Z',
          updated_at: '2026-09-16T00:00:00Z',
        }),
        { status: init?.method === 'POST' ? 201 : 200 },
      ),
  );
  vi.stubGlobal('fetch', fetchMock);

  render(
    <QueryClientProvider client={createQueryClient()}>
      <MemoryRouter initialEntries={['/investigate']}>
        <Routes>
          <Route path="/investigate" element={<Investigate />} />
          <Route path="/investigations/:id" element={<p>Investigation opened</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );

  expect(
    screen.getByText(
      'A company name is enough to start. Add a contact if you also want Sentinel to assess their relationship with the company.',
    ),
  ).toBeInTheDocument();
  expect(screen.getByLabelText(/Contact person/)).not.toBeRequired();

  await userEvent.click(screen.getByRole('button', { name: 'Try public example — ARIE Finance' }));
  expect(screen.getByLabelText(/Company name/)).toHaveValue('ARIE Finance');
  expect(screen.getByLabelText(/Contact person/)).toHaveValue('');
  await userEvent.click(screen.getByRole('button', { name: 'Start Investigation' }));

  await waitFor(() => expect(screen.getByText('Investigation opened')).toBeInTheDocument());
  const request = fetchMock.mock.calls.find(([, init]) => init?.method === 'POST');
  expect(request).toBeDefined();
  expect(JSON.parse(String(request?.[1]?.body))).toEqual({
    company_label: 'ARIE Finance',
    contact_label: '',
    investigation_context: null,
    claims: null,
  });
});

test('sends optional investigation context and claims when supplied', async () => {
  const fetchMock = vi.fn(
    async (_input: RequestInfo | URL, init?: RequestInit) =>
      new Response(
        JSON.stringify({
          investigation_id: 'zen-case',
          company_label: 'Zenith Global Traders Ltd',
          contact_label: '',
          case_type: 'FICTIONAL_TEST_CASE',
          investigation_context: 'Supplier / vendor',
          intake_state: 'SUFFICIENT_FOR_DISCOVERY',
          clarification_reason: null,
          investigation_state: 'NOT_STARTED',
          company_identity_status: null,
          company_match_basis: null,
          completeness_state: null,
          screening_state: null,
          counterparty: null,
          candidates: [],
          entity_candidates: [],
          created_at: '2026-09-16T00:00:00Z',
          updated_at: '2026-09-16T00:00:00Z',
        }),
        { status: init?.method === 'POST' ? 201 : 200 },
      ),
  );
  vi.stubGlobal('fetch', fetchMock);

  render(
    <QueryClientProvider client={createQueryClient()}>
      <MemoryRouter initialEntries={['/investigate']}>
        <Routes>
          <Route path="/investigate" element={<Investigate />} />
          <Route path="/investigations/:id" element={<p>Investigation opened</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );

  await userEvent.type(screen.getByLabelText(/Company name/), 'Zenith Global Traders Ltd');
  await userEvent.selectOptions(
    screen.getByLabelText(/Investigation context/),
    'Supplier / vendor',
  );
  await userEvent.type(screen.getByLabelText(/Claimed operating since/), '2008');
  await userEvent.click(screen.getByRole('button', { name: 'Start Investigation' }));

  await waitFor(() => expect(screen.getByText('Investigation opened')).toBeInTheDocument());
  const request = fetchMock.mock.calls.find(([, init]) => init?.method === 'POST');
  const body = JSON.parse(String(request?.[1]?.body));
  expect(body.investigation_context).toBe('Supplier / vendor');
  expect(body.claims).toEqual({ operating_since_year: '2008' });
});
