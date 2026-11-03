const{chromium}=require('C:/Users/Numerical_Magic_Box/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('node:fs'),zlib=require('node:zlib'),assert=require('node:assert/strict');
(async()=>{const b=await chromium.launch({channel:'msedge',headless:true});try{
 const p=await b.newPage({viewport:{width:1440,height:1000}}),errors=[];p.on('pageerror',e=>errors.push(e.message));
 const original=JSON.parse(fs.readFileSync('work/user-gears-v0122.json','utf8'))[0];
 const edited=structuredClone(original);original.id='original';edited.id='edited';edited.cells.at(-1).code+='\n(* personal note *)';
 original.cells[1].result.execution={operations:null};
 const saved='calix-zlib-v1:'+zlib.deflateSync(Buffer.from(JSON.stringify({version:1,active:'original',documents:[original,edited]})),{level:1}).toString('base64');
 await p.addInitScript(value=>localStorage.setItem('calix-workspace-v1',value),saved);
 await p.goto('http://127.0.0.1:8765');await p.waitForSelector('.engine-status.ready');await p.waitForTimeout(1200);
 let raw=await p.evaluate(()=>localStorage.getItem('calix-workspace-v1'));
 if(raw.startsWith('calix-zlib-v1:'))raw=zlib.inflateSync(Buffer.from(raw.slice(14),'base64')).toString();
 const docs=JSON.parse(raw).documents;
 assert.ok(docs[0].cells.at(-1).code.includes('Block['));
 assert.equal(docs[1].cells.at(-1).code,edited.cells.at(-1).code);
 assert.equal(docs[0].cells[1].result.execution,undefined);
 assert.deepEqual(errors,[]);
 fs.writeFileSync('work/ui-state-v0122-report.json',JSON.stringify({status:'passed',unchangedExampleMigrated:true,editedNotebookPreserved:true,malformedTelemetryDropped:true,errors},null,2));
}finally{await b.close()}})().catch(e=>{console.error(e);process.exitCode=1});
