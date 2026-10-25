import React,{useState} from 'react';
import {useMutation,useQueryClient} from '@tanstack/react-query';
import {ArrowUpRight,Plus,RefreshCw} from 'lucide-react';
import {PageHead,Panel,Button,Field,Status,Loading,ErrorNotice,InlineNote,useToast} from '@arc/ui';
import {credits,dateTime,moneyMinor,billingFigures,paymentDestination} from '@arc/client';
import {api,useScope,useApi} from '../../../app/platform';
import {DataTable} from '../../../modules/analytics/components/Table';

export function Billing(){
 const s=useScope(),cache=useQueryClient(),toast=useToast();
 const[environment,setEnvironment]=useState<'test'|'live'>(s.environment);
 const[month,setMonth]=useState(()=>new Date().toISOString().slice(0,7));
 const[tab,setTab]=useState('usage');
 const path=`/workspaces/${s.wid}/billing`;
 const q=useApi(['billing',s.wid,environment,month],`${path}?environment=${environment}&month=${month}`,true,30_000);
 const checkout=useMutation({mutationFn:async(kind:'credits'|'subscription')=>{
   const key=`arc:checkout:${s.wid}:${kind}`;
   let attempt=sessionStorage.getItem(key);
   if(!attempt){attempt=crypto.randomUUID();sessionStorage.setItem(key,attempt);}
   const result=await api.request(path+'/checkout',{method:'POST',json:{kind},headers:{'Idempotency-Key':attempt}});
   if(result.url){window.location.assign(paymentDestination(result.url));}
   else {sessionStorage.removeItem(key);toast(result.state==='paid'?'This payment is already confirmed. Your balance is up to date.':result.state==='expired'?'That Checkout session expired. Select the purchase again to start a new one.':'This payment needs review. Open the payment history or contact support.');}
   return result;
 },onSuccess:()=>{void cache.invalidateQueries({queryKey:['billing',s.wid]});}});
 const portal=useMutation({mutationFn:async()=>{
   const result=await api.request(path+'/portal',{method:'POST'});
   window.location.assign(paymentDestination(result.url));
 }});
 const d=q.data,fig=billingFigures(d,environment);
 const plan=d?.current_plan??(!d?.subscription?.price_id?{amount_minor:d?.prices.subscription.amount_minor,currency:d?.prices.currency,included_milli:d?.prices.subscription.included_milli}:null);
 return <>
  <PageHead eyebrow="MANAGE" title="Usage & billing" description="Monthly usage, included allowance and prepaid consumption—without counting the same work twice."
   action={<Button variant="secondary" busy={portal.isPending} disabled={!d?.portal_available} onClick={()=>portal.mutate()}>Manage subscription <ArrowUpRight size={14}/></Button>}/>
  <div className="filter-row">
   <Field label="Environment"><select value={environment} onChange={e=>setEnvironment(e.target.value as 'test'|'live')}><option value="test">Test · no cash value</option><option value="live">Live</option></select></Field>
   <Field label="Usage month · UTC"><input type="month" min="2020-01" max={new Date().toISOString().slice(0,7)} value={month} onChange={e=>{if(e.target.value)setMonth(e.target.value);}}/></Field>
   <Button variant="ghost" onClick={()=>q.refetch()}><RefreshCw size={14}/>Refresh</Button>
  </div>
  {q.isLoading&&<Loading/>}{q.error&&<ErrorNotice error={q.error}/>}
  {(checkout.error||portal.error)&&<ErrorNotice error={checkout.error||portal.error}/>}
  {d&&<>
   {!d.prices_approved&&<InlineNote tone="warning">Preview prices only. Live billing is not yet available.</InlineNote>}
   {d.wallets.find((w:any)=>w.environment===environment)?.frozen&&<InlineNote tone="warning">Paid operations are paused while a billing issue is reviewed. Contact support; your records and invoices remain available.</InlineNote>}
   {environment==='test'&&<InlineNote>Test processing uses test credits only. Live subscription allowances and payments are not applied to this view.</InlineNote>}
   <div className="stat-grid">
    {[['Available prepaid credits',fig.available,'Current balance, not historical month-end'],['Credits reserved',fig.reserved,'Held for admitted work; not another charge'],['Included credits remaining',fig.allowance,environment==='live'?'Current paid subscription period':'Live allowance excluded'],['Usage this month',fig.usage,`${credits(fig.included)} included + ${credits(fig.prepaid)} prepaid`]].map(([label,value,hint])=><Panel key={String(label)}><div className="stat-body"><span>{label}</span><strong>{credits(Number(value))}</strong><small>{hint}</small></div></Panel>)}
   </div>
   {d.storage_unsettled_milli>0&&<InlineNote tone="warning">{credits(d.storage_unsettled_milli)} storage credits await settlement. New uploads are restricted until funds are available. Existing files follow their published retention.</InlineNote>}
   {environment==='live'&&<div className="settings-layout">
    <Panel title="Monthly subscription"><div className="panel-body stack">
     <Status value={d.subscription.status}/>
     <div className="key-value"><span>Monthly base price</span><strong>{plan?moneyMinor(plan.amount_minor,plan.currency):'Awaiting price reconciliation'}</strong></div>
     <div className="key-value"><span>Included each paid period</span><strong>{plan?credits(plan.included_milli):'—'} credits</strong></div>
     <div className="key-value"><span>{d.subscription.cancel_at_period_end?'Access ends':'Next renewal'}</span><strong>{dateTime(d.subscription.period_end)}</strong></div>
     <Button disabled={!d.subscription_checkout_available} busy={checkout.isPending} onClick={()=>checkout.mutate('subscription')}>Start subscription</Button>
     {!d.subscription_checkout_available&&<p className="small muted">Subscriptions can be activated when live pricing, payment setup and your workspace's billing eligibility are ready. Test services remain available.</p>}
     <p className="small muted">Renewal follows your actual subscription dates. Usage reports use calendar months in UTC.</p>
    </div></Panel>
    <Panel title="Prepaid credits"><div className="panel-body stack">
     <strong>{credits(d.prices.credit_pack.credits_milli)} credits · {moneyMinor(d.prices.credit_pack.amount_minor,d.prices.currency)}</strong>
     <p>Applied only after included allowance. Spending these credits will not create a second Stripe charge.</p>
     <Button disabled={!d.checkout_available} busy={checkout.isPending} onClick={()=>checkout.mutate('credits')}><Plus size={14}/>Buy credits</Button>
     {!d.checkout_available&&<p className="small muted">Credit purchases are not enabled for this environment yet. You can continue testing with sandbox credits.</p>}
     <p className="small muted">A purchase is activated only after verified payment. Taxes, where configured, appear at Checkout.</p>
    </div></Panel>
   </div>}
   <div className="tabs" role="tablist" aria-label="Billing details">{['usage','ledger',...(environment==='live'?['payments','invoices']:[])].map(name=><button key={name} role="tab" aria-selected={tab===name} onClick={()=>setTab(name)}>{name[0].toUpperCase()+name.slice(1)}</button>)}</div>
   <Panel>
    {(tab==='usage'||environment==='test'&&['payments','invoices'].includes(tab))&&<DataTable data={d.usage.services} columns={[
     {accessorKey:'service',header:'Service'},{accessorKey:'quantity',header:'Units',cell:({row}:any)=>`${row.original.quantity.toLocaleString()} ${row.original.unit}`},
     {accessorKey:'gross_milli',header:'Usage credits',cell:({getValue}:any)=>credits(getValue())},
     {accessorKey:'included_milli',header:'From allowance',cell:({getValue}:any)=>credits(getValue())},
     {accessorKey:'prepaid_milli',header:'From prepaid',cell:({getValue}:any)=>credits(getValue())}]} empty="No settled usage in this month."/>}
    {tab==='ledger'&&<DataTable data={d.ledger} columns={[{accessorKey:'description',header:'Description'},{accessorKey:'kind',header:'Type'},{accessorKey:'amount_milli',header:'Prepaid change',cell:({getValue}:any)=>credits(getValue())},{accessorKey:'created_at',header:'Time',cell:({getValue}:any)=>dateTime(getValue())}]} empty="No credit entries in this month."/>}
    {environment==='live'&&tab==='payments'&&<DataTable data={d.payments} columns={[{accessorKey:'id',header:'Reference'},{accessorKey:'kind',header:'Purchase'},{accessorKey:'amount_minor',header:'Amount',cell:({row}:any)=>moneyMinor(row.original.amount_minor,row.original.currency)},{accessorKey:'state',header:'State',cell:({getValue}:any)=><Status value={getValue()}/>},{accessorKey:'created_at',header:'Created',cell:({getValue}:any)=>dateTime(getValue())}]} empty="No payment attempts yet."/>}
    {environment==='live'&&tab==='invoices'&&<DataTable data={d.invoices} columns={[{accessorKey:'id',header:'Invoice'},{accessorKey:'status',header:'Status',cell:({getValue}:any)=><Status value={getValue()}/>},{accessorKey:'amount_due_minor',header:'Amount due',cell:({row}:any)=>moneyMinor(row.original.amount_due_minor,row.original.currency)},{accessorKey:'amount_paid_minor',header:'Amount paid',cell:({row}:any)=>moneyMinor(row.original.amount_paid_minor,row.original.currency)},{id:'link',header:'Receipt',cell:({row}:any)=>row.original.hosted_url?<a href={row.original.hosted_url} target="_blank" rel="noreferrer">Open invoice ↗</a>:'—'}]} empty="Invoices appear after verified provider events or reconciliation."/>}
   </Panel>
   <Panel title="Published billing rules"><div className="panel-body stack"><p>{d.prices.policy}</p>{d.prices.rates.map((rate:any)=><div key={rate.service}><strong>{rate.service} · {rate.unit}</strong><p>{rate.rate_milli!==undefined?`${credits(rate.rate_milli)} credits per ${rate.unit}`:`${credits(rate.base_milli)} base credits + ${credits(rate.per_kib_milli)} credits per KiB, per step`}</p><p className="small muted">{rate.formula}</p></div>)}<p className="small muted">Price version: {d.prices.version}. {d.reporting_note}</p></div></Panel>
  </>}
 </>;
}
