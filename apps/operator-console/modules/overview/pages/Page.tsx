import React from 'react';
import {Panel,Button,Status,Badge,InlineNote,Empty} from '@arc/ui';
import {Check,AlertTriangle} from 'lucide-react';
import {dateTime} from '@arc/client';
import {SimpleTable} from '../../../app/components/SimpleTable';
export function Page({d,setSelected,setReply}: {d:any;setSelected:(value:any)=>void;setReply:(value:string)=>void}) {
return <>
<><div className="stat-grid">{[['Workspaces',d.customers],['Customer accounts',d.accounts],['Open support requests',d.support_open],['Pending emails',d.pending_mail]].map(([label,value])=><Panel key={label}><div className="stat-body"><span>{label}</span><strong>{value}</strong></div></Panel>)}</div><Panel title="Processing and deployment"><div className="panel-body"><div className="status-list">{Object.entries(d.jobs).map(([k,v])=><div className="key-value" key={k}><Status value={k}/><strong>{String(v)}</strong></div>)}</div><div className="key-value"><span>Deployment mode</span><Badge>{d.deployment.mode}</Badge></div><div className="key-value"><span>Live access</span><Status value={d.deployment.live_enabled?'active':'disabled'}/></div><div className="key-value"><span>Storage adapter</span><strong>{d.deployment.storage}</strong></div><div className="key-value"><span>Failed webhook deliveries</span><strong>{d.failed_deliveries}</strong></div></div></Panel></>
</>
}
