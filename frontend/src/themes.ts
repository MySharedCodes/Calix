import { savePreference } from './preferences';
export type Theme = 'white' | 'black' | 'pink' | 'ocean' | 'forest';
export const themeOptions: {id: Theme; name: string; color: string}[] = [
  {id:'white',name:'简洁白',color:'#f6f8fa'}, {id:'black',name:'深空黑',color:'#16191d'},
  {id:'pink',name:'少女粉',color:'#f8d9e6'}, {id:'ocean',name:'海洋蓝',color:'#b8e6f0'},
  {id:'forest',name:'森林绿',color:'#cbe5ce'},
];
export function applyTheme(theme: Theme) {
  document.documentElement.dataset.theme = theme;
  savePreference('calix-theme', theme);
  window.dispatchEvent(new Event('calix-theme-change'));
}
export function plotPalette() {
  const css = getComputedStyle(document.documentElement);
  return { background: css.getPropertyValue('--plot-bg').trim() || '#f8fafb', text: css.getPropertyValue('--text-muted').trim() || '#52616b', grid: css.getPropertyValue('--border').trim() || '#e3e9ec' };
}
