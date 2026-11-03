const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict'),ts=require('typescript');
(async()=>{
const cortex=await import('@cortex-js/compute-engine');
const cache=new Map(),storage=new Map(),document={documentElement:{lang:''}};
function load(file){
 file=path.resolve(file);if(cache.has(file))return cache.get(file);
 if(file.endsWith('.json'))return JSON.parse(fs.readFileSync(file,'utf8'));
 const module={exports:{}};cache.set(file,module.exports);
 const requireLocal=name=>name==='react'?{useSyncExternalStore:()=>{}}:name==='@cortex-js/compute-engine'?cortex:name.startsWith('.')?load(path.resolve(path.dirname(file),name)+(name.endsWith('.json')?'':'.ts')):require(name);
 vm.runInNewContext(ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true}}).outputText,
  {module,exports:module.exports,require:requireLocal,document,localStorage:{getItem:key=>storage.get(key),setItem:(key,value)=>storage.set(key,value)}},{filename:file});
 return module.exports;
}
const i18n=load('frontend/src/i18n.ts'),extra=load('frontend/src/locales.ts').extraTranslations;
i18n.installTranslations(extra);
for(const locale of ['ja','fr','ru','de','es']){
 const missing=Object.keys(i18n.translations).filter(key=>!extra[locale][key]);assert.deepEqual(missing,[],locale);
 i18n.setLanguage(locale);assert.equal(document.documentElement.lang,locale);assert.equal(i18n.t('保存'),extra[locale]['保存']);
}
i18n.setLanguage('en');
const {latexToWolfram}=load('frontend/src/mathjson.ts'),symbols=load('frontend/src/special-symbols.ts');
assert.equal(symbols.findSpecialSymbol('a').symbol,'α');
assert.equal(symbols.findSpecialSymbol('G').symbol,'Γ');
assert.match(symbols.findSpecialSymbol('intt').template,/\\int/);
assert.equal(symbols.findSpecialSymbol('unknown'),undefined);
assert.equal(symbols.findSpecialSymbol('Alpha').symbol,'α');
assert.equal(symbols.findSpecialSymbol('CapitalAlpha').symbol,'Α');
const aliasOwners=new Map();
assert.equal(new Set(symbols.specialSymbols.map(item=>item.name)).size,symbols.specialSymbols.length);
for(const item of symbols.specialSymbols)for(const alias of item.aliases){assert.ok(!aliasOwners.has(alias),`Duplicate alias: ${alias}`);aliasOwners.set(alias,item.name);}
const expressions=[
 [String.raw`\int x^2\,\mathrm{d}x`,'Integrate[(x^2),x]'],
 [String.raw`\int x^2\,\mathrm{d}\,x`,'Integrate[(x^2),x]'],
 [String.raw`\int_0^1 x^2\,\mathrm{d}x`,'Integrate[(x^2),{x,0,1}]'],
 [String.raw`\sum_{k=1}^{10} k^2`,'Sum[(k^2),{k,1,10}]'],
 [String.raw`\prod_{k=1}^{5} k`,'Product[k,{k,1,5}]'],
 [String.raw`\lim_{x\to 0}\frac{\sin x}{x}`,'Limit[(Sin[x]/x),x->0]'],
 [String.raw`x_{12}+\alpha`,'(x₁₂+α)'],
 [String.raw`\mathcal{A}+\mathfrak{x}`,'(𝒜+𝔵)'],
 [String.raw`\overline{z}`,'Conjugate[z]'],
 [String.raw`\sin\left(90\degree\right)`,'Sin[(90*Pi/180)]'],
 [String.raw`\pi`,'Pi'],
 [String.raw`\int_0^{\pi}\sin x\,\mathrm{d}x`,'Integrate[Sin[x],{x,0,Pi}]'],
 [String.raw`\partial_{x}\left(x^2+y^2\right)`,'D[(((x^2)+(y^2))),x]'],
 [String.raw`\partial_{x}^{2}\left(x^3\right)`,'D[((x^3)),{x,2}]'],
 [String.raw`\begin{pmatrix}1&2\\3&4\end{pmatrix}`,'{{1,2},{3,4}}'],
];
for(const [latex,expected] of expressions)assert.equal(latexToWolfram(latex),expected,latex);
assert.throws(()=>latexToWolfram(String.raw`\int \placeholder{}\,\mathrm{d}x`));
const report={status:'passed',extraLanguages:Object.keys(extra),translatedKeys:Object.keys(i18n.translations).length,symbols:symbols.specialSymbols.length,formulaConversions:expressions.length};
fs.writeFileSync('work/frontend-symbols-v0114-report.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report));
})().catch(error=>{console.error(error);process.exitCode=1;});
