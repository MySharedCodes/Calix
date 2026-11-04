const{chromium}=require(process.env.CALIX_PLAYWRIGHT || 'playwright');
const fs=require('node:fs'),zlib=require('node:zlib'),assert=require('node:assert/strict');
(async()=>{const b=await chromium.launch({channel:'msedge',headless:true});try{
 const p=await b.newPage({viewport:{width:1440,height:1000}}),errors=[];p.on('pageerror',e=>errors.push(e.message));
 const legacy=['v0121','v0122'].map(version=>JSON.parse(fs.readFileSync(`frontend/src/legacy-gear-${version}.json`,'utf8')));
 const docs=legacy.flatMap((item,index)=>{
  const original={format:'calix-notebook',version:1,title:item.title,id:`old-${index}`,path:null,updated:1,cells:item.sources.map((code,i)=>({id:`c${i}`,mode:'source',code}))};
  const edited=structuredClone(original);edited.id=`edited-${index}`;edited.cells.at(-1).code+='\n(* personal note *)';return[original,edited];
 });
 docs[0].cells[0].result={kind:'expression',text:'1',latex:'1',engine:'test',elapsed_ms:0,execution:{operations:null}};
 const saved='calix-zlib-v1:'+zlib.deflateSync(Buffer.from(JSON.stringify({version:1,active:docs[0].id,documents:docs})),{level:1}).toString('base64');
 await p.addInitScript(value=>localStorage.setItem('calix-workspace-v1',value),saved);
 await p.goto(process.env.CALIX_TEST_URL||'http://127.0.0.1:8766');await p.waitForSelector('.engine-status.ready');await p.waitForTimeout(1200);
 let raw=await p.evaluate(()=>localStorage.getItem('calix-workspace-v1'));
 if(raw.startsWith('calix-zlib-v1:'))raw=zlib.inflateSync(Buffer.from(raw.slice(14),'base64')).toString();
 const current=JSON.parse(raw).documents;
 for(let i=0;i<4;i++){if(i%2)assert.equal(current[i].cells.at(-1).code,docs[i].cells.at(-1).code);else assert.ok(current[i].cells.at(-1).code.includes('95*Length[s]/100'));}
 assert.equal(current[0].cells[0].result.execution,undefined);assert.deepEqual(errors,[]);
 fs.writeFileSync('work/ui-state-v0123-report.json',JSON.stringify({status:'passed',legacyVersions:['0.1.21','0.1.22'],unchangedExamplesMigrated:true,editedNotebooksPreserved:true,malformedTelemetryDropped:true,errors},null,2));
}finally{await b.close()}})().catch(e=>{console.error(e);process.exitCode=1});
