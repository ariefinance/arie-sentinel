import { afterEach, describe, expect, test, vi } from 'vitest';
import { ApiError, createApiClient, resolveAuthMode, type TokenProvider } from './api';

afterEach(() => vi.unstubAllGlobals());

const response = () => new Response(JSON.stringify({ status: 'ok' }), { status: 200 });

describe('API authentication boundary', () => {
  test('runtime auth mode defaults safely and permits an explicit demo override', () => {
    expect(resolveAuthMode(false)).toBe('production');
    expect(resolveAuthMode(true)).toBe('development');
    expect(resolveAuthMode(false, 'development')).toBe('development');
    expect(resolveAuthMode(true, 'production')).toBe('production');
    expect(resolveAuthMode(false, 'invalid')).toBe('production');
  });

  test('development sends only the selected dev role header', async () => {
    const fetchMock = vi.fn(
      async (_input: RequestInfo | URL, _init?: RequestInit): Promise<Response> => response(),
    );
    vi.stubGlobal('fetch', fetchMock);
    const client = createApiClient({ mode: 'development', devRole: 'manager' });

    await client.health();

    const headers = fetchMock.mock.calls[0][1]?.headers as Record<string, string>;
    expect(headers['X-Dev-Role']).toBe('manager');
    expect(headers.Authorization).toBeUndefined();
  });

  test('production sends a bearer token and never the dev header', async () => {
    const fetchMock = vi.fn(
      async (_input: RequestInfo | URL, _init?: RequestInit): Promise<Response> => response(),
    );
    vi.stubGlobal('fetch', fetchMock);
    const provider: TokenProvider = {
      getAccessToken: async () => 'deterministic-test-token',
      getRole: () => 'manager',
    };
    const client = createApiClient({ mode: 'production', tokenProvider: provider });

    await client.health();

    expect(client.getCurrentRole()).toBe('manager');
    const headers = fetchMock.mock.calls[0][1]?.headers as Record<string, string>;
    expect(headers.Authorization).toBe('Bearer deterministic-test-token');
    expect(headers['X-Dev-Role']).toBeUndefined();
  });

  test('production fails clearly before fetch when no token is available', async () => {
    const fetchMock = vi.fn(
      async (_input: RequestInfo | URL, _init?: RequestInit): Promise<Response> => response(),
    );
    vi.stubGlobal('fetch', fetchMock);
    const provider: TokenProvider = {
      getAccessToken: async () => null,
      getRole: () => null,
    };
    const client = createApiClient({ mode: 'production', tokenProvider: provider });

    await expect(client.health()).rejects.toMatchObject({
      status: 401,
      message: 'Production authentication token is unavailable.',
    } satisfies Partial<ApiError>);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
