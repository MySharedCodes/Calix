import { mkdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

const destination = resolve(process.argv[2] || 'docs/branding/Calix-logos-30');
mkdirSync(destination, { recursive: true });
const concepts = [
  ['开口 C / Open C', '<path d="M73 25a32 32 0 1 0 0 50"/><path d="m62 39 20 22m0-22L62 61"/>'],
  ['积分之门 / Integral Gate', '<path d="M23 21H12v58h11m54-58h11v58H77M65 23c-25-14-13 68-38 54"/>'],
  ['坐标折线 / Coordinate', '<path d="M20 17v63h64M25 66l19-24 15 13 22-34"/><circle cx="59" cy="55" r="5" fill="var(--accent)" stroke="none"/>'],
  ['交互节点 / Interaction', '<path d="m28 28 44 44M28 72l44-44"/><circle cx="28" cy="28" r="9"/><circle cx="72" cy="28" r="9"/><circle cx="28" cy="72" r="9"/><circle cx="72" cy="72" r="9"/>'],
  ['双括号 / Brackets', '<path d="M35 21H20v58h15m30-58h15v58H65m-27-15 24-28m-24 0 24 28"/>'],
  ['折叠笔记 / Folded Page', '<path d="M26 15h35l16 16v54H26Zm35 0v18h16M38 48h26M38 61h17"/><path d="m56 73 9 8 15-20" stroke="var(--accent)"/>'],
  ['切线 C / Tangent', '<path d="M72 27a31 31 0 1 0 0 46M18 77l64-54"/><circle cx="50" cy="50" r="5" fill="var(--accent)" stroke="none"/>'],
  ['求和之翼 / Sigma', '<path d="M76 21H25l24 29-24 29h51M66 34h14M66 66h14"/>'],
  ['离散序列 / Sequence', '<path d="M18 78h64M25 65V53m17 12V40m17 25V27m17 38V16"/><circle cx="25" cy="53" r="4" fill="var(--accent)"/><circle cx="42" cy="40" r="4" fill="var(--accent)"/><circle cx="59" cy="27" r="4" fill="var(--accent)"/><circle cx="76" cy="16" r="4" fill="var(--accent)"/>'],
  ['光标与解 / Cursor', '<path d="m27 18 48 38-24 3-10 23Zm29 54 13 12M69 22h16m-8-8v16"/>'],
  ['连续函数 / Continuous', '<path d="M14 62c12 0 15-39 29-39s12 54 27 54 14-39 18-39"/><path d="M15 83V17m0 66h72" stroke-width="3"/>'],
  ['矩阵四格 / Matrix', '<path d="M25 17H15v66h10m50-66h10v66H75"/><rect x="32" y="28" width="12" height="12"/><rect x="57" y="28" width="12" height="12"/><rect x="32" y="59" width="12" height="12"/><rect x="57" y="59" width="12" height="12" fill="var(--accent)"/>'],
  ['根号之路 / Radical', '<path d="m13 52 15-7 13 30 20-54h25M63 53h18m-9-9v18"/>'],
  ['立体解析 / Analytic Cube', '<path d="m50 13 33 19v37L50 88 17 69V32Zm0 38 33-19M50 51 17 32m33 19v37"/><path d="m17 69 33-18 33 18" stroke="var(--accent)"/>'],
  ['等号空间 / Equality', '<path d="M28 23 13 50l15 27m44-54 15 27-15 27M38 41h24M38 59h24"/>'],
  ['轨迹焦点 / Trajectory', '<path d="M16 76Q47-14 85 66"/><circle cx="60" cy="28" r="7" fill="var(--accent)"/><path d="M16 85h69" stroke-width="3"/>'],
  ['双曲线 C / Hyperbolic C', '<path d="M80 19H53C10 19 10 81 53 81h27M66 34H50c-23 0-23 32 0 32h16"/>'],
  ['三页笔记 / Three Pages', '<path d="M15 21h22v58H15Zm26 8h22v50H41Zm26 8h18v42H67Z"/><path d="M22 34h8m18 8h8m18 8h5" stroke="var(--accent)" stroke-width="4"/>'],
  ['交叉切面 / Cross Section', '<path d="m50 14 34 36-34 36-34-36Zm-18 36h36M50 32v36"/><circle cx="50" cy="50" r="10" fill="var(--accent)" stroke="none"/>'],
  ['函数映射 / Mapping', '<path d="M23 24c-12 0-12 52 0 52m54-52c12 0 12 52 0 52M32 50h36m-9-10 10 10-10 10"/><circle cx="28" cy="31" r="3" fill="var(--accent)"/><circle cx="72" cy="69" r="3" fill="var(--accent)"/>'],
  ['像素 C / Pixel C', '<path d="M76 22H38v12H25v32h13v12h38V65H43V35h33Z" fill="currentColor" stroke="none"/><rect x="62" y="43" width="15" height="15" fill="var(--accent)" stroke="none"/>'],
  ['极值山脊 / Extremum', '<path d="m14 76 25-50 16 30 11-21 22 41"/><circle cx="39" cy="26" r="7" fill="var(--accent)"/><path d="M24 85h51" stroke-width="3"/>'],
  ['方程折角 / Equation Fold', '<path d="M20 18h60L57 50l23 32H20l23-32Zm15 13h30M35 69h30"/>'],
  ['微分双线 / Differential', '<path d="M66 16 42 82m4-46c-25-8-36 35-14 37 18 2 21-22 21-22M63 43l20 30m0-30L63 73"/>'],
  ['原点 / Origin', '<circle cx="50" cy="50" r="28"/><path d="M50 11v18m0 42v18M11 50h18m42 0h18"/><circle cx="50" cy="50" r="7" fill="var(--accent)" stroke="none"/>'],
  ['编织 CX / Woven CX', '<path d="M48 24C11 10 11 90 48 76M54 25l30 50m0-50L54 75"/><path d="m42 49 16 2" stroke="var(--accent)"/>'],
  ['收敛 / Convergence', '<path d="m15 18 34 32-34 32m36-64 34 32-34 32M13 50h70"/><circle cx="85" cy="50" r="5" fill="var(--accent)" stroke="none"/>'],
  ['负空间 C / Counterform', '<path d="M18 17h64v20H40v26h42v20H18Z" fill="currentColor" stroke="none"/><path d="m60 45 12 12m0-12L60 57" stroke="var(--accent)" stroke-width="5"/>'],
  ['运算核心 / Compute Core', '<rect x="27" y="27" width="46" height="46" rx="5"/><path d="M36 13v14m14-14v14m14-14v14M36 73v14m14-14v14m14-14v14M13 36h14M13 50h14M13 64h14m46-28h14M73 50h14M73 64h14M39 42l22 16m0-16L39 58"/>'],
  ['无限笔触 / Infinity Stroke', '<path d="M49 50c-20-40-51-8-30 15 13 15 30-15 30-15s21-40 35-17c22 36-20 46-35 17Z"/><path d="M30 85h40" stroke="var(--accent)"/>'],
];
const palettes = [['#087e80','#db5a66'],['#254d92','#e6ad35'],['#222a31','#0a9b83'],['#8d3156','#31858c'],['#255b43','#db8051'],['#41556a','#c44d59']];
const designs = concepts.map(([name, body], index) => {
  const id = String(index + 1).padStart(2,'0');
  const [ink, accent] = palettes[index % palettes.length];
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" fill="none" stroke="currentColor" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" style="color:${ink};--accent:${accent}">${body}</svg>`;
  writeFileSync(resolve(destination, `Calix-${id}.svg`), svg);
  return { id, name, svg, ink, accent };
});
writeFileSync(resolve(destination, 'designs.json'), JSON.stringify(designs, null, 2));
const html = `<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Calix · 30 logo concepts</title><style>
*{box-sizing:border-box}body{margin:0;font:14px/1.6 "Segoe UI","Microsoft YaHei",sans-serif;color:#293c45;background:#f3f6f7;letter-spacing:0}header{background:#fff;border-bottom:1px solid #dce5e9;padding:26px 36px}h1{font-size:28px;margin:0;font-weight:650}header p{margin:3px 0 0;color:#6c808a}.controls{display:flex;align-items:center;gap:18px;flex-wrap:wrap;margin-top:16px}button,select{font:inherit;border:1px solid #c8d6db;background:#fff;border-radius:4px;padding:6px 12px;cursor:pointer;color:inherit}button:focus-visible,a:focus-visible{outline:3px solid #56a7a6}.selection{display:flex;align-items:center;justify-content:space-between;gap:20px;padding:24px 36px;border-bottom:1px solid #dce5e9;min-height:156px;background:#fff}.wordmark{display:flex;align-items:center;gap:22px}.wordmark svg{width:84px;height:84px}.wordmark strong{font-size:42px;line-height:1.2}.wordmark small{display:block;font-size:12px;color:#7c8d94}.chosen-details{text-align:right}.chosen-details a{color:#087e80}.grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:15px;padding:26px 36px}.concept{display:block;border:1px solid #dae4e8;background:#fff;border-radius:6px;min-width:0;padding:0;overflow:hidden;text-align:left;transition:border-color .15s,box-shadow .15s}.concept:hover{border-color:#6aa9a9}.concept.selected{border-color:#087e80;box-shadow:0 0 0 2px #087e80}.mark{height:135px;display:flex;align-items:center;justify-content:center}.mark svg{width:86px;height:86px}.caption{border-top:1px solid #edf1f3;padding:10px 12px;display:flex;gap:9px;align-items:baseline}.caption b{color:#087e80;font-size:12px}.caption span{font-size:11px;overflow-wrap:anywhere}.dark .mark{background:#24343c}.dark .mark svg{color:#f0f5f6!important}.mono .mark svg{color:#293c45!important;--accent:#293c45!important}.small .mark svg{width:32px;height:32px}.dark.mono .mark svg{color:#f0f5f6!important;--accent:#f0f5f6!important}footer{padding:0 36px 30px;color:#80929a;font-size:12px}.saved{color:#087e80}@media(max-width:1000px){.grid{grid-template-columns:repeat(3,minmax(0,1fr))}}@media(max-width:600px){header,.selection{padding:18px}.grid{padding:18px;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.selection{flex-wrap:wrap}.chosen-details{text-align:left}.wordmark strong{font-size:32px}.wordmark svg{width:60px;height:60px}.mark{height:110px}.controls{gap:8px}.caption{min-height:62px}footer{padding:0 18px 20px}}
</style><header><h1>Calix</h1><p>Calculation &amp; Interactive Xpressions · 商标方案 01–30</p><div class="controls"><label><input type="checkbox" id="dark"> 深色底</label><label><input type="checkbox" id="mono"> 单色</label><label><input type="checkbox" id="small"> 32 px</label><button id="save">下载选中方案</button><span id="status" role="status"></span></div></header><section class="selection"><div class="wordmark"><div id="preview"></div><div><strong>Calix</strong><small>Calculation &amp; Interactive Xpressions</small></div></div><div class="chosen-details"><b id="selected-name"></b><br><a id="download" download>SVG 矢量源文件</a></div></section><main class="grid" id="grid"></main><footer>30 个独立矢量概念。点击方案查看组合字标；深色、单色及小尺寸模式用于比较识别度。所选编号自动保存在本机。</footer><script>
const designs=${JSON.stringify(designs)};const grid=document.querySelector('#grid');let chosen=localStorage.getItem('calix-logo-choice')||'01';
function select(id){chosen=id;const design=designs.find(d=>d.id===id)||designs[0];document.querySelector('#preview').innerHTML=design.svg;document.querySelector('#selected-name').textContent=design.id+' · '+design.name;document.querySelector('#download').href='Calix-'+design.id+'.svg';document.querySelector('#download').download='Calix-'+design.id+'.svg';grid.querySelectorAll('button').forEach(button=>{button.classList.toggle('selected',button.dataset.id===design.id);button.setAttribute('aria-pressed',String(button.dataset.id===design.id))});localStorage.setItem('calix-logo-choice',design.id)}
designs.forEach(design=>{const button=document.createElement('button');button.className='concept';button.dataset.id=design.id;button.setAttribute('aria-label',design.id+' '+design.name);button.innerHTML='<div class="mark">'+design.svg+'</div><div class="caption"><b>'+design.id+'</b><span>'+design.name+'</span></div>';button.onclick=()=>select(design.id);grid.append(button)});select(chosen);
['dark','mono','small'].forEach(mode=>document.querySelector('#'+mode).onchange=event=>grid.classList.toggle(mode,event.target.checked));document.querySelector('#save').onclick=()=>document.querySelector('#download').click();
</script></html>`;
writeFileSync(resolve(destination,'index.html'), html);
console.log(`Created ${designs.length} vector logo concepts in ${destination}`);
