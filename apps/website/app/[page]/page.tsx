import {notFound} from 'next/navigation';
import Link from 'next/link';
import {ArrowUpRight} from 'lucide-react';
import {pages} from '../../lib/content';
import {Contact,Pricing,Services,Docs,StatusPage} from '../../components/PublicPages';
export function generateStaticParams(){return Object.keys(pages).map(page=>({page}))}
export async function generateMetadata({params}:{params:Promise<{page:string}>}){const{page}=await params;return{title:pages[page]?.title||'Page not found'}}
export default async function Page({params}:{params:Promise<{page:string}>}){const{page}=await params;const content=pages[page];if(!content)notFound();return <main id="content" className={`public-page site-container ${page==='docs'?'docs-page':''}`}><header className="public-page-head"><p className="eyebrow">{content.eyebrow}</p><h1>{content.title}</h1><p>{content.intro}</p></header>{page==='contact'?<Contact/>:page==='pricing'?<Pricing/>:page==='services'?<Services/>:page==='docs'?<Docs/>:page==='status'?<StatusPage/>:<div className="prose">{content.sections?.map(s=><section key={s.title}><h2>{s.title}</h2><p>{s.body}</p></section>)}<Link className="text-button" href="/contact/">Contact the team <ArrowUpRight size={14}/></Link></div>}</main>}
