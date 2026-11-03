const ts = require('typescript');
const fs = require('node:fs');
const vm = require('node:vm');
const context = { exports: {}, require:()=>({default:JSON.parse(fs.readFileSync('frontend/src/example-labels.json','utf8'))}) };
vm.runInNewContext(ts.transpileModule(fs.readFileSync('frontend/src/examples.ts', 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText, context);
for (const example of context.exports.examples) {
  const file = { format: 'calix-notebook', version: 1, title: example.title, cells: example.codes.map((code, i) => ({ id: `example-${i}`, mode: 'source', code: `Clear[a,r,f,v,x,y,t,n];\n${code}` })) };
  fs.writeFileSync(`examples/${example.title}.calix`, JSON.stringify(file, null, 2));
}
console.log(`Exported ${context.exports.examples.length} named example notebooks`);
