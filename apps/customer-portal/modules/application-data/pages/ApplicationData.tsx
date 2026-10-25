import React,{useState} from 'react';
import {PageHead,Panel,Button,Loading,ErrorNotice,InlineNote,CodeBlock,Modal} from '@arc/ui';
import {bytes,dateTime} from '@arc/client';
import {useApi,useScope} from '../../../app/platform';
import {DataTable} from '../../../modules/analytics/components/Table';

export function ApplicationData(){
 const s=useScope();const[collection,setCollection]=useState(''),[cursor,setCursor]=useState(''),[selected,setSelected]=useState<any>(null);
 const base=`/projects/${s.pid}/data`;
 const summary=useApi(['data',s.pid,s.environment],`${base}?environment=${s.environment}`);
 const rows=useApi(['records',s.pid,s.environment,collection,cursor],`${base}/${encodeURIComponent(collection)}?environment=${s.environment}&limit=25${cursor?'&cursor='+encodeURIComponent(cursor):''}`,!!collection);
 return <><PageHead eyebrow="OPERATE" title="Application data" description="Your application's records, isolated by project and environment."/>
  <InlineNote>These are managed application records—not your platform login accounts or an unrestricted SQL database. Access through your own backend with scoped data:read and data:write credentials.</InlineNote>
  {(summary.error||rows.error)&&<ErrorNotice error={summary.error||rows.error}/>}
  <div className="settings-layout"><Panel title="Collections"><div className="panel-body stack">
   {summary.isLoading?<Loading/>:summary.data?.collections.map((item:any)=><Button key={item.name} variant="secondary" onClick={()=>{setCollection(item.name);setCursor('');}}>{item.name} · {item.records} records · {bytes(item.size_bytes)}</Button>)}
   {!summary.isLoading&&!summary.data?.collections.length&&<p>Create your first record through the API to see a collection here.</p>}
  </div></Panel><Panel title="Connect your backend"><CodeBlock language="HTTP" code={'PUT /v1/data/contacts/customer_123\nAuthorization: Bearer SERVER_SIDE_KEY\nIdempotency-Key: one-stable-operation-id\nContent-Type: application/json\n\n{"data":{"name":"Ada"},"expected_version":0}'}/><div className="panel-body"><p>Use the returned version for updates. Reuse the idempotency key when retrying an uncertain write. Data values and retry receipts are encrypted before database storage.</p></div></Panel></div>
  {collection&&<Panel title={collection}>{rows.isLoading?<Loading/>:<DataTable data={rows.data?.items||[]} columns={[{accessorKey:'key',header:'Record'},{accessorKey:'version',header:'Version'},{accessorKey:'size_bytes',header:'Size',cell:({getValue}:any)=>bytes(getValue())},{accessorKey:'updated_at',header:'Updated',cell:({getValue}:any)=>dateTime(getValue())},{id:'inspect',header:'Action',cell:({row}:any)=><Button variant="ghost" onClick={()=>setSelected(row.original)}>Inspect</Button>}]} empty="No records in this collection."/>}<div className="panel-body row-actions"><Button variant="secondary" disabled={!cursor} onClick={()=>setCursor('')}>First page</Button><Button variant="secondary" disabled={!rows.data?.next_cursor} onClick={()=>setCursor(rows.data.next_cursor)}>Next page</Button></div></Panel>}
  <Modal open={!!selected} onClose={()=>setSelected(null)} title={selected?.key||'Record'} description="Authorized access to this collection is audited."><CodeBlock language="json" code={JSON.stringify(selected?.data,null,2)||''}/></Modal>
 </>;
}
