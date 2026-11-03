const ts=require('typescript');
const fs=require('node:fs');
const vm=require('node:vm');
const assert=require('node:assert/strict');
const source=fs.readFileSync('frontend/src/examples.ts','utf8');
const compiled=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText;
const context={exports:{},require:()=>({default:JSON.parse(fs.readFileSync('frontend/src/example-labels.json','utf8'))})};vm.runInNewContext(compiled,context);
const {examples,numericalPools,numericalExample}=context.exports;
assert.equal(numericalPools.length,10);
const validateNumerical=code=>{
 const lines=code.split('\n');assert.equal(lines.length,10);
 for(let i=0;i<10;i++)assert.ok(numericalPools[i].includes(lines[i]));
 assert.match(lines[3],/I/);assert.match(lines[8],/Dot|Inverse|Transpose/);assert.match(lines[9],/^Det\[/);
 assert.ok(!code.includes('Column['));
};
let previous='';
for(let i=0;i<100;i++){
 const code=numericalExample(previous);validateNumerical(code);
 if(previous)code.split('\n').forEach((line,j)=>assert.notEqual(line,previous.split('\n')[j]));
 previous=code;
}
assert.equal(examples.filter(e=>e.title==='单位换算与运算').length,1);
assert.equal(examples.filter(e=>['单位换算','单位运算'].includes(e.title)).length,0);
for(const example of examples)for(const code of example.codes)assert.ok(!/Column\[|Labeled\[/.test(code));
(async()=>{
 let count=0;
 for(const category of context.exports.examples)for(const code of category.codes){
  await fetch('http://127.0.0.1:8765/api/cancel/library-tests',{method:'POST',headers:{'X-Calix-Token':'calix-local-development'}});
  const response=await fetch('http://127.0.0.1:8765/api/evaluate',{method:'POST',headers:{'Content-Type':'application/json','X-Calix-Token':'calix-local-development'},body:JSON.stringify({session:'library-tests',code})});
  const result=await response.json();
  if(!response.ok||!result.ok)throw new Error(`${category.title}: ${code}: ${JSON.stringify(result)}`);
  if(['显式数值计算','单位换算与运算'].includes(category.title)){
   assert.equal(code.split('\n').length,10);assert.equal(result.result.kind,'group');assert.equal(result.result.items.length,10);
   if(category.title==='显式数值计算')validateNumerical(code);
   else result.result.items.forEach(item=>{assert.match(item.text,/\[/);assert.ok(!item.latex.split('[').slice(1).join('[').includes('\\frac'));});
  }
  count++;
 }
 fs.writeFileSync('work/library-report.json',JSON.stringify({status:'passed',examples:count,randomNumericalGroups:100,numericalExpressionsPerGroup:10,unitExpressionsPerGroup:10,allBasicExamplesWithoutColumn:true},null,2));
 console.log(`All ${count} library variants passed`);
})().catch(e=>{console.error(e);process.exit(1);});
