import { strFromU8, strToU8, zlibSync, unzlibSync } from 'fflate';

const prefix = 'calix-zlib-v1:';

export function serializeWorkspace(value: unknown): string {
  const json = JSON.stringify(value);
  if (json.length < 1_000_000) return json;
  const bytes = zlibSync(strToU8(json), { level: 1 });
  let binary = '';
  for (let i = 0; i < bytes.length; i += 32768) {
    binary += String.fromCharCode(...bytes.subarray(i, i + 32768));
  }
  return prefix + btoa(binary);
}

export function parseWorkspace(value: string): unknown {
  if (!value.startsWith(prefix)) return JSON.parse(value);
  const bytes = Uint8Array.from(atob(value.slice(prefix.length)), c => c.charCodeAt(0));
  const inflated = unzlibSync(bytes);
  return JSON.parse(strFromU8(inflated));
}
