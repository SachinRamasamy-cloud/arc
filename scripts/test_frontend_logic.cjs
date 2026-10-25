/** Execute dependency-free shared TypeScript logic with Node, not a browser. */
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
let ts;try{ts=require('typescript')}catch{ts=require(process.env.ARC_TYPESCRIPT_PATH||'typescript')}
const root=path.resolve(__dirname,'..');
function load(relative,dependency={}){const exports={};const text=ts.transpileModule(fs.readFileSync(path.join(root,relative),'utf8'),{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS}}).outputText;vm.runInNewContext(text,{exports,require:n=>dependency[n],Headers,Response,AbortSignal,fetch:global.fetch,console,URL,Intl,Date,Number,JSON,Error},{filename:relative});return exports}
const core=load('packages/client/src/core.ts');let passed=0;
async function test(name,fn){await fn();passed++;console.log('PASS '+name)}
(async()=>{
 await test('unknown error cannot display internal exception',()=>{const e=core.normalizeError({code:'SQL_ERROR',detail:'password=secret'},500);assert.equal(e.code,'INTERNAL_ERROR');assert(!e.message.includes('secret'))});
 await test('validation fields never reflect raw input messages',()=>{const e=core.normalizeError({code:'INVALID_INPUT',fields:[{field:'name',message:'sensitive'}]},422);assert.equal(e.fields[0].message,'Check this value.')});
 await test('request references only accept expected identifiers',()=>{assert.equal(core.normalizeError({request_id:'<script>'},500).requestId,'');assert.equal(core.normalizeError({request_id:'req_'+'a'.repeat(32)},500).requestId,'req_'+'a'.repeat(32))});
 await test('credit formatting uses milli-credits',()=>{assert.equal(core.credits(9123),'9.123');assert.equal(core.credits(NaN),'—')});
 await test('file size and date formatting handle empty input',()=>{assert.equal(core.bytes(1024),'1.0 KB');assert.equal(core.bytes(-1),'—');assert.equal(core.dateTime(), '—');assert(core.dateTime(1700000000).length>4)});
 await test('JSON and CSV parsing remain distinct',()=>{assert.equal(core.parseData('a,b\n1,2','csv_to_json'),'a,b\n1,2');assert.equal(core.parseData('{"a":1}','validate').a,1);assert.throws(()=>core.parseData('bad','validate'))});
 await test('events deduplicate sort and bound history',()=>{const a=[{id:2,type:'node.running',data:{}}];assert.equal(core.appendEvent(a,a[0]),a);let b=core.appendEvent(a,{id:1,type:'queued',data:{}},1);assert.equal(b.length,1);assert.equal(b[0].id,2)});
 await test('role controls match least privilege',()=>{assert(core.allowed('owner','finance'));assert(core.allowed('developer','build'));assert(!core.allowed('viewer','keys'));assert(!core.allowed('unknown','read'));assert(!core.allowed('billing','build'))});
 const sdk=load('sdk/typescript/index.ts');let count=0;
 const transport=async(url,init)=>{count++;assert.equal(new Headers(init.headers).get('Authorization'),'Bearer private');if(init.method==='POST'){assert.equal(new Headers(init.headers).get('Idempotency-Key'),'same-op');return new Response(JSON.stringify({job:{id:'run_a1',state:'queued'},created:true}),{status:202})}return new Response(JSON.stringify({job:{id:'run_a1',state:'succeeded'}}))};
 const client=new sdk.ArcClient('https://api.example.test/','private',transport);
 await test('TypeScript SDK submits real HTTP contract',async()=>{const value=await client.run({operation:'validate',data:[]},'same-op');assert.equal(value.job.id,'run_a1');assert.equal(count,1)});
 await test('SDK fetches status without replaying submission',async()=>{assert.equal((await client.job('run_a1')).job.state,'succeeded');assert.equal(count,2)});
 await test('SDK rejects missing credentials keys and traversal',()=>{assert.throws(()=>new sdk.ArcClient('x',''));assert.throws(()=>client.run({operation:'validate'},''));assert.throws(()=>client.job('../keys'))});
 await test('SDK errors never expose upstream detail',async()=>{const c=new sdk.ArcClient('https://api.example.test','private',async()=>new Response(JSON.stringify({detail:'secret',code:'private/path'}),{status:500}));await assert.rejects(c.job('run_a1'),e=>e.code==='INTERNAL_ERROR'&&!e.message.includes('secret'))});
 console.log(`${passed} shared-logic/SDK checks passed. React rendering, third-party type resolution and WebGL were not tested.`);
})().catch(e=>{console.error(e);process.exitCode=1});
