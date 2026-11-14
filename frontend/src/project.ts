// GitHub repository IDs survive account/repository renames and transfers.
export const githubRepositoryId = 1445077152;
export const githubFallbackUrl = 'https://github.com/MySharedCodes/Calix';

export async function projectRepositoryUrl(): Promise<string> {
  try {
    const response = await fetch(`https://api.github.com/repositories/${githubRepositoryId}`, {
      signal: AbortSignal.timeout(4000), headers: { Accept: 'application/vnd.github+json' },
    });
    if (!response.ok) return githubFallbackUrl;
    const repository = await response.json();
    if (repository.id === githubRepositoryId && typeof repository.html_url === 'string'
      && /^https:\/\/github\.com\/[\w.-]+\/[\w.-]+$/.test(repository.html_url)) return repository.html_url;
  } catch { /* Offline or rate limited: GitHub also redirects former names. */ }
  return githubFallbackUrl;
}

export async function openProjectRepository(desktop: boolean): Promise<void> {
  // Reserve the browser tab during the user gesture to avoid popup blockers.
  const tab = desktop ? null : window.open('about:blank', '_blank');
  if (tab) tab.opener = null;
  try {
    const url = await projectRepositoryUrl();
    if (desktop) {
      const { invoke } = await import('@tauri-apps/api/core');
      await invoke('open_project_repository', { url });
    } else if (tab) tab.location.replace(url);
    else throw new Error('Browser blocked the GitHub window');
  } catch (error) { tab?.close(); throw error; }
}
