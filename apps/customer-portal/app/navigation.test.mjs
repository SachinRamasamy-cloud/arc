import test from 'node:test';
import assert from 'node:assert/strict';
import {allDestinations,findGroup,searchDestinations,docsDestination} from './navigation.ts';

test('every portal destination is unique and docs is directly findable',()=>{
 const items=allDestinations();
 assert.equal(new Set(items.map(i=>i.id)).size,items.length);
 assert.equal(searchDestinations('openapi',items)[0].id,'docs');
 assert.equal(searchDestinations('invoice',items)[0].id,'billing');
 assert.equal(searchDestinations('invite',items)[0].id,'team');
 assert.equal(searchDestinations('R2',items)[0].id,'files');
});
test('workspace browsing does not require a project and protected operations do',()=>{
 const map=Object.fromEntries(allDestinations().map(i=>[i.id,i]));
 for(const id of ['overview','services','team','billing','docs']) assert.equal(map[id].project,false,id);
 for(const id of ['studio','playground','keys','executions']) assert.equal(map[id].project,true,id);
 assert.equal(map.team.permission,'read');
 assert.equal(findGroup('team'),'WORKSPACE');
 assert.equal(docsDestination.id,'docs');
});
test('navigation search remains bounded and returns no irrelevant items',()=>{
 const items=allDestinations();
 assert.deepEqual(searchDestinations('definitely-unknown',items),[]);
 assert.ok(searchDestinations('',items).length <= 9);
 assert.ok(searchDestinations('bill',items).every(i=>i.label.toLowerCase().includes('bill')||i.aliases?.some(a=>a.toLowerCase().includes('bill'))));
});
