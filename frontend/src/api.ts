import { t } from './i18n';
import type { Result } from './types';
export const desktop = '__TAURI_INTERNALS__' in window;
let connection: { port: number; token: string } | null = null;

export async function connect() {
  if (desktop) {
    const { invoke } = await import('@tauri-apps/api/core');
    connection = await invoke('connection_info');
  } else {
    connection = { port: 0, token: sessionStorage.getItem('calix-token') || new URLSearchParams(location.search).get('token') || 'calix-local-development' };
  }
  const health = await request('/health');
  return health as { native: boolean; version: string; cpu_count: number; max_workers: number; components: { pde: boolean; languages: boolean; themes: boolean } };
}

async function request(path: string, body?: unknown) {
  if (!connection) throw new Error(t("计算引擎尚未连接"));
  const origin = connection.port ? `http://127.0.0.1:${connection.port}` : '';
  const response = await fetch(`${origin}/api${path}`, {
    method: body === undefined ? 'GET' : 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Calix-Token': connection.token },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail));
  return data;
}

export async function evaluate(session: string, code: string): Promise<Result> {
  const response = await request('/evaluate', { session, code, request_id: crypto.randomUUID() });
  if (!response.ok) throw new Error(response.error);
  return response.result;
}

export async function cancel(session: string) { return request(`/cancel/${session}`, {}); }
export async function configureWorkers(max_workers: number) { return request('/settings', { max_workers }); }
export async function componentResource(name: 'languages' | 'themes') { return request(`/components/${name}`); }
export async function openUI(notebook?: string) { return request('/open-ui', { notebook }); }
