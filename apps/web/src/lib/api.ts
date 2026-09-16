import type {
  AuditEventOut,
  CreateInvestigationBody,
  FindingOut,
  HealthOut,
  InvestigationOut,
  Role,
  ScreeningResultOut,
  SourceOut,
  WorklistFilter,
  WorklistItem,
} from './types';

const API_BASE = '/api';
const DEV_ROLE: Role = import.meta.env.VITE_DEV_ROLE === 'manager' ? 'manager' : 'analyst';

export interface TokenProvider {
  getAccessToken(): Promise<string | null>;
  getRole(): Role | null;
}

export type AuthMode = 'development' | 'production';

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
}

interface ApiClientOptions {
  mode: AuthMode;
  tokenProvider?: TokenProvider;
  devRole?: Role;
}

let configuredTokenProvider: TokenProvider | null = null;

export function configureTokenProvider(provider: TokenProvider): void {
  configuredTokenProvider = provider;
}

const runtimeTokenProvider: TokenProvider = {
  getAccessToken: async () => configuredTokenProvider?.getAccessToken() ?? null,
  getRole: () => configuredTokenProvider?.getRole() ?? null,
};

export function createApiClient({
  mode,
  tokenProvider = runtimeTokenProvider,
  devRole = DEV_ROLE,
}: ApiClientOptions) {
  async function authHeaders(): Promise<Record<string, string>> {
    if (mode === 'development') return { 'X-Dev-Role': devRole };
    const token = await tokenProvider.getAccessToken();
    if (!token) {
      throw new ApiError(401, 'Production authentication token is unavailable.', '');
    }
    return { Authorization: `Bearer ${token}` };
  }

  async function send(path: string, options: RequestOptions = {}): Promise<Response> {
    const { method = 'GET', body, signal } = options;
    const headers: Record<string, string> = {
      Accept: 'application/json',
      ...(await authHeaders()),
    };
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    try {
      return await fetch(`${API_BASE}${path}`, {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
        signal,
      });
    } catch (cause) {
      throw new ApiError(
        0,
        'Network request failed. The service may be unreachable.',
        String(cause),
      );
    }
  }

  async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const response = await send(path, options);
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

  async function requestBlob(path: string, body: unknown): Promise<Blob> {
    const response = await send(path, { method: 'POST', body });
    if (!response.ok) {
      throw new ApiError(
        response.status,
        `Report failed (${response.status}).`,
        await response.text(),
      );
    }
    return response.blob();
  }

  return {
    getCurrentRole: (): Role | null => (mode === 'development' ? devRole : tokenProvider.getRole()),
    health: (signal?: AbortSignal): Promise<HealthOut> => request<HealthOut>('/health', { signal }),
    createInvestigation: (body: CreateInvestigationBody): Promise<InvestigationOut> =>
      request<InvestigationOut>('/investigations', { method: 'POST', body }),
    getInvestigation: (id: string, signal?: AbortSignal): Promise<InvestigationOut> =>
      request<InvestigationOut>(`/investigations/${encodeURIComponent(id)}`, { signal }),
    getAudit: (id: string, signal?: AbortSignal): Promise<AuditEventOut[]> =>
      request<AuditEventOut[]>(`/investigations/${encodeURIComponent(id)}/audit`, { signal }),
    getSources: (id: string, signal?: AbortSignal): Promise<SourceOut[]> =>
      request<SourceOut[]>(`/investigations/${encodeURIComponent(id)}/sources`, { signal }),
    getScreening: (id: string, signal?: AbortSignal): Promise<ScreeningResultOut[]> =>
      request<ScreeningResultOut[]>(`/investigations/${encodeURIComponent(id)}/screening`, {
        signal,
      }),
    getFindings: (id: string, signal?: AbortSignal): Promise<FindingOut[]> =>
      request<FindingOut[]>(`/investigations/${encodeURIComponent(id)}/findings`, { signal }),
    resolveEntity: (
      id: string,
      candidateId: string,
      rationale: string,
    ): Promise<InvestigationOut> =>
      request<InvestigationOut>(`/investigations/${encodeURIComponent(id)}/resolve-entity`, {
        method: 'POST',
        body: { candidate_id: candidateId, rationale },
      }),
    reviewScreening: (
      id: string,
      disposition: string,
      rationale: string,
    ): Promise<ScreeningResultOut> =>
      request<ScreeningResultOut>(`/screening-results/${encodeURIComponent(id)}/review`, {
        method: 'POST',
        body: { disposition, rationale },
      }),
    reviewFinding: (id: string, disposition: string, rationale: string): Promise<FindingOut> =>
      request<FindingOut>(`/findings/${encodeURIComponent(id)}/review`, {
        method: 'POST',
        body: { disposition, rationale },
      }),
    createReport: (id: string): Promise<Blob> =>
      requestBlob(`/investigations/${encodeURIComponent(id)}/report`, {
        confirm_finalise: true,
      }),
    getWorklist: (filter: WorklistFilter, signal?: AbortSignal): Promise<WorklistItem[]> =>
      request<WorklistItem[]>(`/worklist?filter=${encodeURIComponent(filter)}`, { signal }),
  };
}

const runtimeMode: AuthMode = import.meta.env.DEV ? 'development' : 'production';
export const api = createApiClient({ mode: runtimeMode });

export { DEV_ROLE };
