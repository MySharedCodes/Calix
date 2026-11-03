import { mkdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

const destination = resolve(process.argv[2] || 'docs/branding/Calix-logos-100');
mkdirSync(destination, { recursive: true });
const p = (d, extra = '') => `<path d="${d}" ${extra}/>`;
const c = (x,y,r,extra='') => `<circle cx="${x}" cy="${y}" r="${r}" ${extra}/>`;
const r = (x,y,w,h,extra='') => `<rect x="${x}" y="${y}" width="${w}" height="${h}" ${extra}/>`;
const accent = 'stroke="var(--accent)"';
const solid = 'fill="currentColor" stroke="none"';
const dot = (x,y,size=5) => c(x,y,size,'fill="var(--accent)" stroke="none"');
const families = [
  ['C 字母构形', [
    ['切角开环', p('M78 22H34L18 38v24l16 16h44M67 35H42L31 46v8l11 11h25')],
    ['双重切口', p('M77 27a32 32 0 1 0 0 46M66 36a20 20 0 1 0 0 28')+p('m77 27-8 9m0 28 8 9',accent)],
    ['折线回声', p('M80 19H30L14 50l16 31h50L64 65H41l-8-15 8-15h23Z',solid)],
    ['阶梯入口', p('M80 18H46v12H30v15H18v22h12v15h50V67H47V33h33Z',solid)],
    ['平行弧带', p('M77 18C8 1 8 99 77 82M72 31C29 20 29 80 72 69')+dot(78,50,6)],
    ['方圆相接', p('M78 24H48a26 26 0 0 0 0 52h30M77 24v14m0 24v14')+p('M52 40v20m-10-10h20',accent)],
    ['细长回转', p('M76 18H43C8 18 8 82 43 82h33M63 31H45C27 31 27 69 45 69h18', 'stroke-width="4"')+p('M63 44h20M63 56h20',accent)],
    ['六边留白', p('M78 20H36L15 50l21 30h42V63H46l-9-13 9-13h32Z',solid)],
    ['断续圆章', p('M73 23a32 32 0 0 0-43 5M20 44a32 32 0 0 0 10 28M47 82a32 32 0 0 0 26-9','stroke-width="10"')+dot(78,49,7)],
    ['折页 C', p('M79 20H26v60h53V64H43V36h36Z',solid)+p('m43 36-17-16M43 64 26 80','stroke="#fff" stroke-width="3"')],
  ]],
  ['CX 组合字母', [
    ['共用中轴', p('M48 22H31L17 50l14 28h17M48 22l35 56m0-56L48 78')],
    ['交织双带', p('M47 23C8 14 8 86 47 77M51 25l31 50M82 25 51 75','stroke-width="10"')+p('m55 45 12 11','stroke="#fff" stroke-width="3"')],
    ['斜切组合', p('M46 20H25L12 50l13 30h21M60 20l24 60m3-60L57 80')+p('M38 50h27',accent)],
    ['方块互锁', p('M46 22H17v56h29V64H31V36h15M56 22l28 56m0-56L56 78','stroke-linecap="square"')],
    ['双向折线', p('M47 23 17 50l30 27M60 23l25 54m0-54L60 77')+dot(58,50,4)],
    ['相切双字', p('M48 28a25 25 0 1 0 0 44M53 20l29 60m0-60L53 80')+p('M49 46v8',accent)],
    ['数学斜体', p('M49 26C22 13 6 82 36 78M64 23C54 37 72 65 83 77M86 23C69 34 63 62 48 77','stroke-width="5"')],
    ['路径编译', p('M46 21H24L13 50l11 29h22M56 21v18l25 22v18M81 21v18L56 61v18')],
    ['正负切面', p('M46 18H17v64h29V67H32V33h14Z',solid)+p('m56 29 27 42m0-42L56 71','stroke-width="9"')],
    ['对称端点', p('M43 25H26L14 50l12 25h17M57 25l29 50m0-50L57 75')+c(43,25,4)+c(43,75,4)+dot(71.5,50,5)],
  ]],
  ['微积分语言', [
    ['双积分', p('M46 19C24 9 42 91 20 81M79 19C57 9 75 91 53 81')+p('M33 50h35',accent)],
    ['积分交点', p('M66 16C28 3 66 98 30 84M17 50h66')+dot(48,50,6)],
    ['偏微分', p('M31 23C76 3 86 83 46 82 9 81 18 38 52 43c17 2 19 15 10 26')],
    ['极限括弧', p('M32 18C9 18 9 82 32 82M68 18c23 0 23 64 0 64M38 36l24 28m0-28L38 64')],
    ['求和折面', p('M79 18H22l27 32-27 32h57V66H49l14-16-14-16h30Z',solid)],
    ['差分阶跃', p('M15 78V58h18V39h18V20h33')+p('M15 88h69M84 20v68','stroke-width="2"')+dot(51,39)],
    ['导数切线', p('M16 75C35 75 37 20 83 20M20 85l58-70')+dot(48,47,6)],
    ['根号折返', p('m15 52 12-10 15 34 20-55h24M64 38h20M64 53h15','stroke-linejoin="miter"')],
    ['分式空间', p('M18 50h64M38 24l24 13m0-13L38 37M38 65h24M50 59v20')],
    ['连续极限', p('M14 67c25 0 14-34 36-34s11 34 36 34M18 18v64m0 0h68','stroke-width="4"')+p('M27 50h46','stroke-dasharray="3 7" '+accent)],
  ]],
  ['函数与轨迹', [
    ['阻尼振动', p('M13 51c8-48 16 48 24 0s16 32 24 0 16 16 26 0')+p('M13 82h74','stroke-width="2"')],
    ['抛物折射', p('M17 79Q50-35 83 79M24 42h53','stroke-width="5"')+dot(50,22,6)],
    ['李萨如结', p('M15 50C15 3 85 97 85 50S15 97 15 50Z')+dot(50,50,5)],
    ['指数阶梯', p('M16 79C57 79 73 65 83 17M16 70v9h10M37 65v14M58 53v26M77 30v49','stroke-width="4"')],
    ['正交双曲', p('M18 18v64h64M28 23c3 30 20 40 49 42M28 65c29-2 46-12 49-42','stroke-width="4"')],
    ['驻点之环', p('M16 65c14-58 30-58 42 0s21-1 27-23')+c(36,27,7,accent)],
    ['轨迹分叉', p('M17 78C36 78 34 22 80 22M17 78c31 0 28-24 63-24')+dot(80,22)+dot(80,54)],
    ['极坐标花结', p('M50 50C10-2 5 55 50 50c-45 5 11 53 0 0 11 53 46 3 0 0 46 3 2-52 0 0Z','stroke-width="4"')],
    ['样条弯折', p('M18 71C16 20 46 19 48 48s34 29 34-21')+r(12,65,12,12,accent)+r(76,21,12,12,accent)],
    ['相位差', p('M14 40c18-39 35 39 53 0s19 0 19 0M14 65c18 39 35-39 53 0s19 0 19 0','stroke-width="5"')],
  ]],
  ['线性代数', [
    ['行列透视', p('M21 17v66m58-66v66M35 30h30M35 50h30M35 70h30')+dot(35,30)+dot(50,50)+dot(65,70)],
    ['对角跃迁', r(20,20,60,60,'rx="3"')+p('M40 20v60M60 20v60M20 40h60M20 60h60','stroke-width="2"')+p('m27 73 46-46',accent)],
    ['基底向量', p('M22 76V20m0 56h57M22 76l48-43m-1-10 3 12-13 1M14 31l8-12 8 12M68 68l12 8-12 8')],
    ['块矩阵', r(17,17,27,27,solid)+r(56,17,27,27)+r(17,56,27,27)+r(56,56,27,27,'fill="var(--accent)" stroke="none"')],
    ['转置翻折', p('M20 18v64h62M36 18h46v46M36 64V18M36 64h46','stroke-width="4"')+p('m26 74 48-48m-12 0h12v12',accent)],
    ['特征方向', p('M17 80V20h63v60ZM17 80l63-60M17 50h63M49 20v60','stroke-width="3"')+p('M17 80 69 28',accent+' stroke-width="7"')],
    ['正交投影', p('M19 77h62M19 77V16M30 64l45-39M75 25v52','stroke-width="4"')+p('M65 77V67h10',accent)+dot(75,25,5)],
    ['秩的阶层', p('M18 77V24h18v53M43 77V38h18v39M68 77V52h18v25','stroke-width="5"')+p('M15 85h74',accent)],
    ['三角分解', p('M20 20h60v60H20ZM20 20l60 60M20 40h20M20 60h40M40 80V60M60 80V60','stroke-width="4"')],
    ['矩阵乘积', p('M13 22v56m74-56v56M25 34h12v12H25Zm38 20h12v12H63ZM43 44l14 12m0-12L43 56','stroke-width="5"')],
  ]],
  ['空间与曲面', [
    ['旋转坐标', p('m50 18 30 49H20Zm0 0v64M20 67l60-33M20 34l60 33','stroke-width="4"')],
    ['等轴折纸', p('M17 35 50 16l33 19v30L50 84 17 65Zm0 0 33 20 33-20M50 55v29M34 25v30l33 20','stroke-width="4"')],
    ['双曲鞍面', p('M16 25Q50 81 84 25L71 78Q50 40 29 78ZM22 43Q50 75 78 43M27 61q23-4 46 0','stroke-width="4"')],
    ['三轴展开', p('M50 50V15M50 50l34 25M50 50 16 75M41 27l9-12 9 12m13 35 12 13-17-1M33 74l-17 1 12-13')+dot(50,50,6)],
    ['环面剖切', '<ellipse cx="50" cy="50" rx="35" ry="24"/><ellipse cx="50" cy="50" rx="16" ry="9"/>'+p('M15 50c10 38 60 38 70 0M50 26v15M50 59v15','stroke-width="4"')],
    ['四面推演', p('m50 14 36 65H14Zm0 0v44L14 79m36-21 36 21M14 79h72','stroke-width="4"')],
    ['剖面之窗', p('m50 15 33 19v39L50 88 17 69V34Zm-18 30 18 10 18-10v20L50 75 32 65Z','stroke-width="4"')+p('M50 15v20m0 40v13',accent)],
    ['等高山丘', '<ellipse cx="50" cy="59" rx="35" ry="21"/><ellipse cx="50" cy="50" rx="25" ry="16"/><ellipse cx="50" cy="40" rx="14" ry="10"/>'+dot(50,30,4)],
    ['参数经纬', c(50,50,33)+p('M17 50h66M50 17c-25 20-25 46 0 66m0-66c25 20 25 46 0 66M24 31q26 16 52 0M24 69q26-16 52 0','stroke-width="3"')],
    ['投影方格', p('m16 36 45-18 23 46-45 18Zm15-6 23 46M46 24l23 46M24 52l45-18M32 67l45-18','stroke-width="4"')],
  ]],
  ['笔记与表达式', [
    ['书页映射', p('M50 24C37 15 25 15 14 21v55c12-6 24-6 36 3 12-9 24-9 36-3V21c-11-6-23-6-36 3Zm0 0v55','stroke-width="4"')+p('M26 39h12M62 39h12M26 53h12M62 53h12',accent+' stroke-width="3"')],
    ['行间函数', p('M24 17h52v66H24ZM35 31h30M35 69h30M35 50l9-8 11 16 10-8','stroke-width="4"')],
    ['分页计算', p('M20 18h48v64H20ZM31 33h26M31 47h17M31 61h26M68 31h14v51H68','stroke-width="4"')+dot(75,68,4)],
    ['代码书签', p('M24 16h52v68L50 70 24 84ZM43 32 33 43l10 11m14-22 10 11-10 11','stroke-width="5"')],
    ['折角求和', p('M22 17h37l19 19v47H22ZM59 17v19h19M62 47H36l13 13-13 13h26','stroke-width="4"')],
    ['同步双栏', p('M16 23h29v54H16Zm39 0h29v54H55ZM29 35v30M68 35v30M23 50h12M62 50h12','stroke-width="4"')],
    ['单元接力', r(16,18,53,22,'rx="3"')+r(31,60,53,22,'rx="3"')+p('M43 40v10h14v10M26 29h21M44 71h21','stroke-width="4"')],
    ['笔尖坐标', p('m50 14 25 35-12 31H37L25 49Zm0 0v33M37 80h26M45 58l5-11 5 11','stroke-width="4"')+dot(50,50,4)],
    ['表达式分层', p('M18 21h64v18H18Zm0 40h64v18H18ZM28 30h12M60 70h12M41 39v11h18v11','stroke-width="4"')],
    ['打开的证明', p('M18 20h28v60H18m64-60H54v60h28M30 35l7 7-7 7M65 61h9','stroke-width="5"')],
  ]],
  ['交互与求解', [
    ['拖动控制点', p('M19 75C20 25 80 75 81 25','stroke-width="5"')+r(13,69,12,12)+r(75,19,12,12)+c(50,50,9,accent)],
    ['求解路径', p('M16 24h28v24h27v27h13M16 24v54h28M71 48V24h13','stroke-width="5"')+dot(44,48,6)],
    ['边界收敛', p('M16 18h22v64H16M84 18H62v64h22M38 50h24M44 40l10 10-10 10','stroke-width="5"')],
    ['局部搜索', c(43,42,24)+p('m61 60 23 23M29 45l9 8 18-21')+dot(55,32,4)],
    ['插入焦点', p('M28 16H16v22m56-22h12v22M16 62v22h12m56-22v22H72M34 50h32M50 34v32','stroke-width="5"')],
    ['推演箭头', p('M18 29h35V17l30 33-30 33V71H18M18 43h27M18 57h27','stroke-width="5"')],
    ['节点联立', c(25,25,9)+c(75,25,9)+c(50,76,9)+p('m30 33 16 35m24-35L54 68M34 25h32','stroke-width="4"')+dot(50,44,5)],
    ['可执行括号', p('M29 18H16v64h13m42-64h13v64H71M41 31l25 19-25 19Z','stroke-width="5"')],
    ['迭代回路', p('M19 45c0-34 62-34 62 0M19 55c0 34 62 34 62 0M9 34l10 12 11-12m40 32 11-12 10 12','stroke-width="5"')+p('M41 44h18M41 56h18',accent)],
    ['滑块函数', p('M16 29h68M16 71h68M16 50h68','stroke-width="3"')+r(29,20,12,18,solid)+r(60,41,12,18,solid)+r(41,62,12,18,'fill="var(--accent)" stroke="none"')],
  ]],
  ['几何与负形', [
    ['三角切口', p('m50 14 36 68H14Zm0 26L36 67h28Z', 'fill="currentColor" fill-rule="evenodd" stroke="none"')+dot(50,57,4)],
    ['错位方环', p('M17 17h50v16H33v34H17ZM83 83H33V67h34V33h16Z',solid)],
    ['双菱交汇', p('m36 18 26 32-26 32L10 50Zm28 0 26 32-26 32-26-32Z','stroke-width="5"')],
    ['六片折面', p('m50 13 33 19v36L50 87 17 68V32Zm0 0v74M17 32l66 36M17 68l66-36','stroke-width="4"')+p('m50 50 33-18v36Z','fill="var(--accent)" stroke="none"')],
    ['十字留白', p('M18 18h25v25H18Zm39 0h25v25H57ZM18 57h25v25H18Zm39 0h25v25H57Z',solid)],
    ['偏心圆段', p('M82 50a32 32 0 1 1-32-32v16a16 16 0 1 0 16 16Z',solid)+p('M63 18h19v19H63Z','fill="var(--accent)" stroke="none"')],
    ['旋转折带', p('M20 20h60v16H36v44H20ZM80 80H49V64h15V49h16Z',solid)],
    ['三重楔形', p('m15 20 28 30-28 30h18l28-30-28-30Zm33 0 28 30-28 30h18l28-30-28-30Z',solid)],
    ['正交弧角', p('M18 48V18h30M52 18h30v30M82 52v30H52M48 82H18V52','stroke-width="8"')+p('M34 50a16 16 0 1 0 16-16',accent)],
    ['中心裂隙', p('M18 17h27v66H18Zm37 0h27v66H55Z',solid)+p('m40 31 20 19-20 19','stroke="#fff" stroke-width="5"')],
  ]],
  ['字标与徽记', [
    ['小写连字', '<text x="12" y="60" font-family="Georgia,serif" font-size="37" font-weight="bold" fill="currentColor" stroke="none">cx</text>'+p('M17 73h66',accent+' stroke-width="4"')],
    ['大写错层', '<text x="13" y="53" font-family="Arial,sans-serif" font-size="42" font-weight="bold" fill="currentColor" stroke="none">C</text><text x="48" y="80" font-family="Arial,sans-serif" font-size="42" font-weight="bold" fill="var(--accent)" stroke="none">X</text>'],
    ['细线字章', '<text x="17" y="65" font-family="Arial,sans-serif" font-size="38" fill="currentColor" stroke="none">CX</text>'+p('M17 21h66M17 79h66','stroke-width="3"')],
    ['衬线积分字', '<text x="12" y="67" font-family="Georgia,serif" font-size="52" fill="currentColor" stroke="none">C</text>'+p('M80 20C61 10 75 91 56 81','stroke-width="4" '+accent)],
    ['窄体方章', r(15,15,70,70,'rx="2" stroke-width="3"')+'<text x="24" y="63" font-family="Arial,sans-serif" font-size="34" font-weight="bold" fill="currentColor" stroke="none">Cx</text>'],
    ['负形字模', r(13,20,74,60,solid)+'<text x="23" y="63" font-family="Arial,sans-serif" font-size="35" font-weight="bold" fill="#fff" stroke="none">CX</text>'],
    ['下标方程', '<text x="15" y="63" font-family="Georgia,serif" font-size="49" font-style="italic" fill="currentColor" stroke="none">C</text><text x="58" y="78" font-family="Georgia,serif" font-size="31" font-style="italic" fill="var(--accent)" stroke="none">x</text>'],
    ['括号字标', p('M25 22H14v56h11m50-56h11v56H75','stroke-width="4"')+'<text x="30" y="64" font-family="Georgia,serif" font-size="40" fill="currentColor" stroke="none">C</text>'],
    ['Calix 手册', '<text x="10" y="58" font-family="Arial,sans-serif" font-size="29" font-weight="bold" fill="currentColor" stroke="none">calix</text>'+p('M12 71h76M12 25h28','stroke-width="4" '+accent)],
    ['等式签名', '<text x="8" y="56" font-family="Georgia,serif" font-size="29" font-style="italic" fill="currentColor" stroke="none">Calix</text>'+p('M32 69h36M32 79h36','stroke-width="4" '+accent)],
  ]],
];
const palettes = [['#067a7a','#de6571'],['#284f8c','#d6a130'],['#284e3e','#db8057'],['#853b59','#258a95'],['#26353d','#18a08d']];
let index = 31;
const designs = families.flatMap(([family, entries], familyIndex) => entries.map(([name,body], variant) => {
  const id = String(index++).padStart(3,'0');
  const [ink, color] = palettes[(familyIndex + variant) % palettes.length];
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" style="color:${ink};--accent:${color}" role="img" aria-label="Calix ${id}">${body}</svg>`;
  writeFileSync(resolve(destination, `Calix-${id}.svg`), svg);
  return { id, family, name, svg, ink, accent: color };
}));
if (designs.length !== 100 || new Set(designs.map(d=>d.svg.replace(/style="[^"]*"|aria-label="[^"]*"/g,''))).size !== 100) throw new Error('Expected 100 distinct designs');
writeFileSync(resolve(destination,'designs.json'), JSON.stringify(designs,null,2));
const css = `*{box-sizing:border-box}body{margin:0;color:#293e46;background:#f3f6f7;font:14px/1.6 "Segoe UI","Microsoft YaHei",sans-serif;letter-spacing:0}button,input,select{font:inherit;color:inherit}button{cursor:pointer}button,select,input[type=search]{background:#fff;border:1px solid #cbd8dd;border-radius:4px;padding:7px 10px}button:hover{border-color:#218b89}button:focus-visible,a:focus-visible,input:focus-visible,select:focus-visible{outline:3px solid #55aaa5;outline-offset:2px}header{background:#fff;padding:24px 32px 20px;border-bottom:1px solid #dce5e8}h1{font-size:28px;line-height:1.3;margin:0 0 5px}header p{margin:0;color:#788d96}nav{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-top:20px}nav label{display:flex;align-items:center;gap:5px}input[type=search]{width:220px;max-width:100%}.preview-band{display:flex;align-items:center;justify-content:space-between;gap:20px;padding:22px 32px;background:#fff;border-bottom:1px solid #dce5e8}.wordmark{display:flex;align-items:center;gap:20px;min-width:0}.wordmark svg{width:80px;height:80px;flex-shrink:0}.wordmark strong{font-size:38px;line-height:1.3}.wordmark small{font-size:11px;display:block;color:#80929a}.details{text-align:right;line-height:1.9}.details a{color:#067a7a}.count{padding:15px 32px 0;color:#7b8f97;font-size:12px}.family{padding:20px 32px 4px}.family h2{font-size:14px;font-weight:600;margin:0 0 12px;display:flex;gap:12px;align-items:baseline}.family h2 span{font-size:11px;font-weight:400;color:#8a9ba2}.grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:13px}.concept{position:relative;background:#fff;border:1px solid #dae4e7;border-radius:5px;min-width:0;overflow:hidden}.concept.selected{outline:2px solid #087e80;outline-offset:0}.mark-button{display:flex;width:100%;height:124px;align-items:center;justify-content:center;border:0;border-radius:0}.mark-button svg{width:80px;height:80px;overflow:visible}.caption{padding:9px 11px;border-top:1px solid #edf1f3;display:flex;align-items:center;gap:8px;min-height:41px;font-size:11px}.caption b{color:#067a7a;font-variant-numeric:tabular-nums}.caption span{flex:1;min-width:0;overflow-wrap:anywhere}.favorite{position:absolute;right:7px;top:7px;border:0;padding:2px;width:27px;height:27px;font-size:20px;color:#8ca0a8;background:#ffffffde}.favorite[aria-pressed=true]{color:#b38a21}.dark .mark-button{background:#263940}.dark .mark-button svg{color:#edf5f6!important}.mono .mark-button svg{color:#293e46!important;--accent:#293e46!important}.dark.mono .mark-button svg{color:#edf5f6!important;--accent:#edf5f6!important}.small .mark-button svg{width:32px;height:32px}.empty{padding:40px 32px;color:#8a9ba2}footer{padding:25px 32px 35px;color:#8a9ba2;font-size:12px}dialog{border:1px solid #cbd8dd;border-radius:6px;width:1000px;max-width:calc(100% - 32px);padding:20px;color:inherit}dialog::backdrop{background:#253b4655}.dialog-head{display:flex;align-items:center;justify-content:space-between;gap:15px;margin-bottom:16px}.comparison{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}.compare-item{text-align:center;border-bottom:1px solid #dce5e8;padding:15px}.compare-item svg{width:110px;height:110px}.compare-item strong{display:block;font-size:22px}.compare-item small{display:block;font-size:9px}.compare-item p{font-size:12px;margin:10px 0 0}.contact header,.contact .preview-band,.contact footer,.contact .count{display:none}.contact .family{padding:18px 25px 0}.contact .family h2{margin-bottom:8px}.contact .grid{grid-template-columns:repeat(10,minmax(0,1fr));gap:8px}.contact .mark-button{height:95px}.contact .mark-button svg{width:67px;height:67px}.contact .caption{padding:6px;min-height:32px;font-size:10px;gap:5px}.contact .favorite{display:none}.contact:before{content:'Calix · Calculation & Interactive Xpressions / 031–130';display:block;padding:18px 25px 0;font-size:22px;font-weight:600}@media(max-width:900px){.grid{grid-template-columns:repeat(4,minmax(0,1fr))}.comparison{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:600px){header{padding:20px 17px}nav{gap:9px}.family{padding:18px 17px 0}.grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.preview-band{padding:18px 17px;flex-wrap:wrap}.wordmark svg{width:60px;height:60px}.wordmark strong{font-size:29px}.wordmark small{font-size:9px}.details{text-align:left}.count{padding-left:17px}.mark-button{height:116px}.comparison{grid-template-columns:1fr}footer{padding-left:17px;padding-right:17px}}`;
const html = String.raw`<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Calix 商标方案 · 031–130</title><style>${css}</style><body><header><h1>Calix · 100 个新商标方案</h1><p>Calculation &amp; Interactive Xpressions · 031–130</p><nav><select id="family" aria-label="设计方向"><option value="">全部方向</option>${families.map(([name])=>`<option>${name}</option>`).join('')}</select><input type="search" id="search" aria-label="搜索编号或名称" placeholder="搜索编号或名称"><label><input type="checkbox" id="saved-only"> 仅收藏</label><label><input type="checkbox" id="dark"> 深色底</label><label><input type="checkbox" id="mono"> 单色</label><label><input type="checkbox" id="small"> 32 px</label><button id="compare">对比收藏</button><button id="export-list">导出收藏清单</button></nav></header><section class="preview-band"><div class="wordmark"><div id="preview"></div><div><strong>Calix</strong><small>Calculation &amp; Interactive Xpressions</small></div></div><div class="details"><b id="selected-name"></b><br><span id="selected-family"></span><br><a id="download" download>下载 SVG</a></div></section><div class="count" id="count" role="status"></div><main id="gallery"></main><footer>本批方案编号 031–130，前批 01–30 保留。收藏及当前选择自动记忆。各方案提供独立 SVG 文件。</footer><dialog id="comparison-dialog"><div class="dialog-head"><strong>收藏方案对比</strong><button id="close-dialog" aria-label="关闭对比">关闭</button></div><div id="comparison" class="comparison"></div></dialog><script>
const designs=${JSON.stringify(designs)};const gallery=document.querySelector('#gallery');const state={family:'',search:'',savedOnly:false};let selected=localStorage.getItem('calix-logo-100-selected')||'031';let favorites;try{favorites=new Set(JSON.parse(localStorage.getItem('calix-logo-100-favorites')||'[]').filter(id=>designs.some(d=>d.id===id)))}catch{favorites=new Set()}
function choose(id){const d=designs.find(item=>item.id===id)||designs[0];selected=d.id;localStorage.setItem('calix-logo-100-selected',selected);document.querySelector('#preview').innerHTML=d.svg;document.querySelector('#selected-name').textContent=d.id+' · '+d.name;document.querySelector('#selected-family').textContent=d.family;const link=document.querySelector('#download');link.href='Calix-'+d.id+'.svg';link.download='Calix-'+d.id+'.svg';gallery.querySelectorAll('.concept').forEach(el=>{el.classList.toggle('selected',el.dataset.id===selected);el.querySelector('.mark-button').setAttribute('aria-pressed',String(el.dataset.id===selected))})}
function render(){gallery.replaceChildren();const filtered=designs.filter(d=>(!state.family||d.family===state.family)&&(!state.savedOnly||favorites.has(d.id))&&(!state.search||(d.id+' '+d.name+' '+d.family).includes(state.search)));document.querySelector('#count').textContent='显示 '+filtered.length+' / 100 个方案 · 已收藏 '+favorites.size+' 个';const groups=[...new Set(filtered.map(d=>d.family))];groups.forEach(family=>{const section=document.createElement('section');section.className='family';const items=filtered.filter(d=>d.family===family);section.innerHTML='<h2>'+family+'<span>'+items[0].id+'–'+items.at(-1).id+'</span></h2><div class="grid"></div>';const grid=section.querySelector('.grid');items.forEach(d=>{const item=document.createElement('article');item.className='concept';item.dataset.id=d.id;item.innerHTML='<button class="mark-button" aria-label="选择 '+d.id+' '+d.name+'">'+d.svg+'</button><button class="favorite" aria-label="收藏 '+d.id+'" aria-pressed="'+favorites.has(d.id)+'">'+(favorites.has(d.id)?'★':'☆')+'</button><div class="caption"><b>'+d.id+'</b><span>'+d.name+'</span></div>';item.querySelector('.mark-button').onclick=()=>choose(d.id);item.querySelector('.favorite').onclick=()=>{favorites.has(d.id)?favorites.delete(d.id):favorites.add(d.id);localStorage.setItem('calix-logo-100-favorites',JSON.stringify([...favorites]));render()};grid.append(item)});gallery.append(section)});if(!filtered.length)gallery.innerHTML='<p class="empty">没有符合条件的方案</p>';choose(selected)}
document.querySelector('#family').onchange=e=>{state.family=e.target.value;render()};document.querySelector('#search').oninput=e=>{state.search=e.target.value.trim();render()};document.querySelector('#saved-only').onchange=e=>{state.savedOnly=e.target.checked;render()};['dark','mono','small'].forEach(mode=>document.querySelector('#'+mode).onchange=e=>gallery.classList.toggle(mode,e.target.checked));document.querySelector('#compare').onclick=()=>{const target=document.querySelector('#comparison');target.replaceChildren();const items=designs.filter(d=>favorites.has(d.id));if(!items.length)target.textContent='尚未收藏方案';items.forEach(d=>{const item=document.createElement('div');item.className='compare-item';item.innerHTML=d.svg+'<strong>Calix</strong><small>Calculation &amp; Interactive Xpressions</small><p>'+d.id+' · '+d.name+'</p>';target.append(item)});document.querySelector('#comparison-dialog').showModal()};document.querySelector('#close-dialog').onclick=()=>document.querySelector('#comparison-dialog').close();document.querySelector('#export-list').onclick=()=>{const content=designs.filter(d=>favorites.has(d.id)).map(d=>d.id+' · '+d.name+' / '+d.family).join('\n');const link=document.createElement('a');link.href=URL.createObjectURL(new Blob([content||'尚未收藏方案'],{type:'text/plain;charset=utf-8'}));link.download='Calix-收藏方案.txt';link.click();setTimeout(()=>URL.revokeObjectURL(link.href),1000)};if(new URLSearchParams(location.search).has('contact'))document.body.classList.add('contact');render();
</script></body></html>`;
writeFileSync(resolve(destination,'index.html'),html);
writeFileSync(resolve(destination,'README.txt'),'Calix 商标方案 031–130\n打开 index.html 比较、收藏并下载方案。SVG 文件可独立使用。\n共 100 个新方案，分为十个设计方向。前批 01–30 不变。\n');
console.log(`Created ${designs.length} new logo concepts (${designs[0].id}–${designs.at(-1).id}) in ${destination}`);
