/** Regression tests for Playground payload construction and field configuration. */
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const ts = require('typescript');
const root = path.resolve(__dirname, '..');
function load(relative, dependencies={}) {
  const exports = {};
  const source = fs.readFileSync(path.join(root, relative), 'utf8');
  const js = ts.transpileModule(source, {compilerOptions:{target:ts.ScriptTarget.ES2022, module:ts.ModuleKind.CommonJS}}).outputText;
  vm.runInNewContext(js, {exports, require:name=>dependencies[name], TextEncoder, Error, Set, Object, Number, Math}, {filename:relative});
  return exports;
}
const core = load('packages/client/src/core.ts');
const helper = load('packages/client/src/playground.ts', {'./core':core});
let passed=0;
function test(name, fn) {fn(); console.log('PASS '+name); passed++;}
const base = {
  operation:'normalize', input:'[{"name":" Ada ","email":" ADA@EXAMPLE.TEST "}]',
  requiredFields:'',lowercaseFields:'email',mappings:[],maxCredits:'10'
};
test('normalization submits user JSON rather than operation identifier', ()=>{
  const result=helper.buildPlaygroundRequest(base);
  assert.equal(result.data[0].name,' Ada ');
  assert.equal(result.data[0].email,' ADA@EXAMPLE.TEST ');
  assert.equal(result.operation,'normalize');
  assert.equal(result.max_credits_milli,10000);
});
test('new input fields and rename mapping are sent to backend', ()=>{
  const result=helper.buildPlaygroundRequest({...base,
    input:'[{"company_name":" ARC ","contact":" INFO@EXAMPLE.TEST "}]',
    lowercaseFields:'email',mappings:[{source:'contact',target:'email'}]});
  assert.equal(result.data[0].company_name,' ARC ');
  assert.equal(result.mappings.contact,'email');
  assert.equal(result.lowercase[0],'email');
});
test('field detection works with custom records',()=>{
  const result=helper.discoverFields('[{"any_new_key":"value"}]','validate');
  assert.deepEqual([...result],['any_new_key']);
});
test('CSV input stays a string instead of JSON parsing',()=>{
  const result=helper.buildPlaygroundRequest({...base, operation:'csv_to_json', input:'name,email\nAda,a@example.com'});
  assert.equal(result.data,'name,email\nAda,a@example.com');
});
test('JSON conversion supports arrays of records',()=>{
  const result=helper.buildPlaygroundRequest({...base, operation:'json_to_csv'});
  assert.equal(result.operation,'json_to_csv');
  assert.equal(result.data[0].name,' Ada ');
});
test('validation submits required fields',()=>{
  const result=helper.buildPlaygroundRequest({...base,operation:'validate',requiredFields:'name, email, name'});
  assert.deepEqual(Array.from(result.required_fields),['name','email']);
});
test('file reference skips inline body without exposing file contents',()=>{
  const result=helper.buildPlaygroundRequest({...base,fileId:'file_8cb4',input:'INVALID_JSON'});
  assert.equal(result.data,null);assert.equal(result.file_id,'file_8cb4');
});
test('invalid JSON fails locally, no request can be sent',()=>{
  assert.throws(()=>helper.buildPlaygroundRequest({...base,input:'not-json'}), /Enter valid JSON/);
});
test('duplicate mappings are rejected',()=>{
  assert.throws(()=>helper.buildPlaygroundRequest({...base,mappings:[{source:'a',target:'x'},{source:'b',target:'x'}]}),/used more than once/);
});
test('blank destination mapping is rejected',()=>{
  assert.throws(()=>helper.buildPlaygroundRequest({...base,mappings:[{source:'name',target:' '}] }),/valid source and destination/);
});
test('invalid credits and oversized data are rejected',()=>{
  assert.throws(()=>helper.buildPlaygroundRequest({...base,maxCredits:'NaN'}),/maximum cost/);
  assert.throws(()=>helper.buildPlaygroundRequest({...base,maxCredits:'0.0001'}),/maximum cost/);
  assert.throws(()=>helper.buildPlaygroundRequest({...base,input:'"'+ 'x'.repeat(1_500_010)+'"'}),/exceeds 1.5 MB/);
});
test('refuses unrecognized operations',()=>{
  assert.throws(()=>helper.buildPlaygroundRequest({...base,operation:'delete_all'}),/not supported/);
});
console.log(`${passed} Playground request/fields regression tests passed.`);
