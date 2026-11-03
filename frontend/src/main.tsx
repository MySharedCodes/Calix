import { createRoot } from 'react-dom/client';
import { restorePreferences } from './preferences';
import { restoreDiskWorkspace } from './recovery-store';
import 'katex/dist/katex.min.css';
import './styles.css';
import './notebook.css';
import './workflow.css';
import './workspace.css';
import './theme-base.css';

async function start() {
  await restorePreferences().catch(console.error);
  await restoreDiskWorkspace().catch(console.error);
  const { default: App } = await import('./App');
  createRoot(document.getElementById('root')!).render(<App />);
}
void start();
