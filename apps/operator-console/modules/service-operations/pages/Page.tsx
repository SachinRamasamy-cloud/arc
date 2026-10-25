import React from 'react';
import {Panel,Button,Status,Badge,InlineNote,Empty} from '@arc/ui';
import {Check,AlertTriangle} from 'lucide-react';
import {dateTime} from '@arc/client';
import {SimpleTable} from '../../../app/components/SimpleTable';
export function Page({d,setSelected,setReply}: {d:any;setSelected:(value:any)=>void;setReply:(value:string)=>void}) {
return <>
<><InlineNote>{d.change_policy}</InlineNote><div className="service-grid">{d.items.map((p:any)=><Panel key={p.id} title={p.name} action={<Badge>{p.status}</Badge>}><div className="panel-body"><p>{p.description}</p><div className="tag-list">{p.operations.map((op:string)=><code key={op}>{op}</code>)}</div></div></Panel>)}</div></>
</>
}
