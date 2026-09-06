/*
 * Typed API client for the ARIE Sentinel backend.
 *
 * All calls go through the `/api` prefix, which the Vite dev server proxies to
 * http://localhost:8000 (and which a reverse proxy handles in production). The
 * dev role header is attached to every request.
 */

import type {
  AuditEventOut,
  CreateInvestigationBody,
  HealthOut,
  InvestigationOut,
  Role,
  WorklistFilter,
  WorklistItem,
} from './types';

const API_BASE = '/api';

// Stage 1 uses a fixed dev role header. A later stage replaces this with real auth.
const DEV_ROLE: Role = 'analyst';

export class ApiError extends Error {
  readonly status: number;
  readonly body: string;

  constructor(status: number, message: string, body: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.body = body;
  }
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  signal?: AbortSignal;
  role?: Role;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, signal, role = DEV_ROLE } = options;

  const headers: Record<string, string> = {
    Accept: 'application/json',
    'X-Dev-Role': role,
  };
  if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal,
    });
  } catch (cause) {
    throw new ApiError(0, 'Network request failed. The service may be unreachable.', String(cause));
  }

  const text = await response.text();

  if (!response.ok) {
    let message = `Request failed (${response.status}).`;
    try {
      const parsed = JSON.parse(text) as { detail?: unknown; message?: unknown };
      const detail = parsed.detail ?? parsed.message;
      if (typeof detail === 'string') message = detail;
    } catch {
      // Non-JSON error body — keep the generic message.
    }
    throw new ApiError(response.status, message, text);
  }

  if (!text) return undefined as T;
  return JSON.parse(text) as T;
}

export const api = {
  health: (signal?: AbortSignal): Promise<HealthOut> => request<HealthOut>('/health', { signal }),

  createInvestigation: (body: CreateInvestigationBody): Promise<InvestigationOut> =>
    request<InvestigationOut>('/investigations', { method: 'POST', body }),

  getInvestigation: (id: string, signal?: AbortSignal): Promise<InvestigationOut> =>
    request<InvestigationOut>(`/investigations/${encodeURIComponent(id)}`, { signal }),

  getAudit: (id: string, signal?: AbortSignal): Promise<AuditEventOut[]> =>
    request<AuditEventOut[]>(`/investigations/${encodeURIComponent(id)}/audit`, { signal }),

  getWorklist: (filter: WorklistFilter, signal?: AbortSignal): Promise<WorklistItem[]> =>
    request<WorklistItem[]>(`/worklist?filter=${encodeURIComponent(filter)}`, { signal }),
};

export { DEV_ROLE };
