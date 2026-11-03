const keys = ['calix-digits','calix-workers','calix-language','calix-theme','calix-notebook-zoom'] as const;
let pending = Promise.resolve();

export async function restorePreferences() {
  if (typeof window === 'undefined' || !('__TAURI_INTERNALS__' in window)) return;
  const { invoke } = await import('@tauri-apps/api/core');
  const saved = await invoke<Record<string,string>>('read_preferences');
  for (const key of keys) if (typeof saved[key] === 'string') localStorage.setItem(key,saved[key]);
}

export function savePreference(key: typeof keys[number], value: string) {
  localStorage.setItem(key,value);
  if (typeof window === 'undefined' || !('__TAURI_INTERNALS__' in window)) return;
  const snapshot = Object.fromEntries(keys.flatMap(name => {
    const item = localStorage.getItem(name); return item === null ? [] : [[name,item]];
  }));
  pending = pending.catch(() => {}).then(async () => {
    const { invoke } = await import('@tauri-apps/api/core');
    await invoke('write_preferences',{preferences:snapshot});
  }).catch(error => { console.error('Could not persist Calix preferences',error); });
}
