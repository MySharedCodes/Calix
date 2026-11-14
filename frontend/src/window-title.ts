import type { Language } from './i18n';

export const windowTitles: Record<Language, string> = {
  zh: 'Calix:开源、轻量、快捷的符号计算',
  en: 'Calix: Open-source, lightweight, fast symbolic computation',
  ja: 'Calix: オープンソース・軽量・高速な数式処理',
  fr: 'Calix : calcul symbolique libre, léger et rapide',
  ru: 'Calix: открытые, лёгкие и быстрые символьные вычисления',
  de: 'Calix: quelloffene, schlanke und schnelle symbolische Berechnungen',
  es: 'Calix: cálculo simbólico abierto, ligero y rápido',
};

export async function updateWindowTitle(language: Language, desktop: boolean) {
  const title = windowTitles[language];
  document.title = title;
  if (desktop) {
    const { getCurrentWindow } = await import('@tauri-apps/api/window');
    await getCurrentWindow().setTitle(title);
  }
}
