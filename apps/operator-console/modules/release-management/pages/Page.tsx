import React from 'react';
import {Panel,Button,Status,Badge,InlineNote,Empty} from '@arc/ui';
import {Check,AlertTriangle} from 'lucide-react';
import {dateTime} from '@arc/client';
import {SimpleTable} from '../../../app/components/SimpleTable';
export function Page({d,setSelected,setReply}: {d:any;setSelected:(value:any)=>void;setReply:(value:string)=>void}) {
return <>
<><InlineNote tone="warning">These are configuration checks, not proof of production readiness. The release qualification report and independent security review are still required.</InlineNote><Panel>{d.checks.map((c:any)=><div className="check-row" key={c.name}>{c.passed?<Check size={17}/>:<AlertTriangle size={17}/>}<span>{c.name}</span><Badge tone={c.passed?'success':'warning'}>{c.passed?'Configured':'Not ready'}</Badge></div>)}</Panel></>
</>
}
