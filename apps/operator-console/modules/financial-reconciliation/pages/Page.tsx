import React from 'react';
import {Panel,Button,Status,Badge,InlineNote,Empty} from '@arc/ui';
import {Check,AlertTriangle} from 'lucide-react';
import {dateTime} from '@arc/client';
import {SimpleTable} from '../../../app/components/SimpleTable';
export function Page({d,setSelected,setReply}: {d:any;setSelected:(value:any)=>void;setReply:(value:string)=>void}) {
return <>
<Panel><SimpleTable headings={['Payment','Workspace','Kind','Amount','State']} rows={d.items.map((p:any)=>[<code>{p.id}</code>,<code>{p.workspace_id}</code>,p.kind,new Intl.NumberFormat(undefined,{style:'currency',currency:p.currency}).format(p.amount_minor/100),<Status value={p.state}/>])}/></Panel>
</>
}
