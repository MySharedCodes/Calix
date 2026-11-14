import { useState } from 'react';
import { Code2, ExternalLink, Star } from 'lucide-react';
import { desktop } from './api';
import { t } from './i18n';
import { githubFallbackUrl, openProjectRepository } from './project';

export function OpenSourceNotice({ onError }: { onError: (message: string) => void }) {
  const [opening, setOpening] = useState(false);
  return <section className="open-source-card" aria-label={t('开源软件')}>
    <div className="open-source-title"><Code2 size={18} /><span>{t('开源软件')}</span></div>
    <p>{t('Calix 以 GPLv3 开源。如果它对你有帮助，欢迎到 GitHub 点亮一颗星，支持项目继续发展。')}</p>
    <a href={githubFallbackUrl} target="_blank" rel="noopener noreferrer" aria-disabled={opening} onClick={event => {
      event.preventDefault();
      if (opening) return;
      setOpening(true);
      void openProjectRepository(desktop).catch(error => onError(String(error))).finally(() => setOpening(false));
    }}><Star size={16} /><span>{t(opening ? '正在打开 GitHub…' : '在 GitHub 上点亮星星')}</span><ExternalLink size={14} /></a>
  </section>;
}
