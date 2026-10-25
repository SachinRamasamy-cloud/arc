import React,{useState,useEffect} from 'react';
import {useNavigate} from '@tanstack/react-router';
import {useMutation} from '@tanstack/react-query';
import {ArrowRight,LockKeyhole,Eye,EyeOff,ArrowLeft,Check,ShieldCheck} from 'lucide-react';
import {Brand,Button,Field,ErrorNotice,InlineNote,Reveal,CodeBlock} from '@arc/ui';
import {api,queryClient} from '../../../app/platform';
export function Auth({mode}:{mode:string}){
 const navigate=useNavigate();const[name,setName]=useState('');const[email,setEmail]=useState('');const[password,setPassword]=useState('');const[code,setCode]=useState('');const[terms,setTerms]=useState(false);const[show,setShow]=useState(false);const[done,setDone]=useState(false);
 const token=new URLSearchParams(location.search).get('token')||'';
 const titles:Record<string,string>={login:'Welcome back.',signup:'Build your next idea.', 'forgot-password':'Reset your password.', 'reset-password':'A fresh start.', 'verify-email':'Verify your account.', 'accept-invite':'Join your workspace.'};
 const descriptions:Record<string,string>={login:'Your services, projects and next great build.',signup:'One workspace. A direct connection to your next product.','forgot-password':'We will send you a secure, single-use reset link.','reset-password':'Choose a new password to secure your account.','verify-email':'Confirm your email address to start building.','accept-invite':'Sign in with the invited email address before accepting.'};
 const action=useMutation({mutationFn:()=>{
  if(mode==='login')return api.request('/auth/login',{method:'POST',json:{email,password,code}});
  if(mode==='signup')return api.request('/auth/signup',{method:'POST',json:{email,password,name,accept_terms:terms}});
  if(mode==='forgot-password')return api.request('/auth/forgot-password',{method:'POST',json:{email}});
  if(mode==='reset-password')return api.request('/auth/reset-password',{method:'POST',json:{token,password}});
  if(mode==='verify-email')return api.request('/auth/verify-email',{method:'POST',json:{token}});
  return api.request('/invitations/accept',{method:'POST',json:{token}});
 },onSuccess:()=>{if(mode==='login'){queryClient.clear();void navigate({to:'/'});}else setDone(true);}});
 const needsCode=action.error && 'code' in action.error && action.error.code==='MFA_REQUIRED';
 return <div className="auth-page"><div className="auth-story"><Brand/><div className="auth-orbit" aria-hidden="true"><div/><div/><span><LockKeyhole size={32}/></span></div><div><p className="eyebrow">YOUR APPLICATION. OUR INFRASTRUCTURE.</p><h2>Less infrastructure.<br/>More possibility.</h2><p>Connect secure APIs, follow the work, and keep every credit under control.</p></div><div className="auth-foot"><ShieldCheck size={14}/><span>Scoped access. Clear costs. Your data.</span></div></div><main className="auth-main"><a className="auth-back" href={import.meta.env.VITE_SITE_URL||'http://127.0.0.1:3000'}><ArrowLeft size={15}/> Back to Arc</a><Reveal className="auth-form"><div className="auth-mobile-brand"><Brand/></div><p className="eyebrow">{mode==='login'?'YOUR WORKSPACE AWAITS':'START WITH SOMETHING REAL'}</p><h1>{titles[mode]}</h1><p>{descriptions[mode]}</p>{done?<div className="auth-success"><div className="empty-icon"><Check/></div><h3>{mode==='signup'?'Check your inbox.':mode==='forgot-password'?'Check your email.':'You’re all set.'}</h3><p>{action.data?.message||'Your workspace invitation has been accepted.'}</p><a className="button button-primary" href="/login">Continue to sign in <ArrowRight size={14}/></a></div>:<form className="form-grid" onSubmit={e=>{e.preventDefault();action.mutate();}}>
 {mode==='signup'&&<Field label="Your name"><input name="name" autoComplete="name" required maxLength={80} value={name} onChange={e=>setName(e.target.value)} placeholder="Alex Morgan"/></Field>}
 {['login','signup','forgot-password'].includes(mode)&&<Field label="Email address"><input type="email" name="email" autoComplete="email" required value={email} onChange={e=>setEmail(e.target.value)} placeholder="you@company.com"/></Field>}
 {['login','signup','reset-password'].includes(mode)&&<Field label="Password" hint={mode!=='login'?'Use at least 12 characters. A passphrase works well.':undefined}><div className="password-field"><input type={show?'text':'password'} autoComplete={mode==='login'?'current-password':'new-password'} minLength={mode==='login'?1:12} maxLength={128} required value={password} onChange={e=>setPassword(e.target.value)} placeholder="Enter your password"/><button type="button" aria-label={show?'Hide password':'Show password'} onClick={()=>setShow(!show)}>{show?<EyeOff size={16}/>:<Eye size={16}/>}</button></div></Field>}
 {(needsCode||code)&&<Field label="Authenticator or recovery code"><input autoComplete="one-time-code" required value={code} onChange={e=>setCode(e.target.value)} placeholder="Enter your code"/></Field>}
 {mode==='signup'&&<label className="checkbox-row"><input type="checkbox" required checked={terms} onChange={e=>setTerms(e.target.checked)}/><span>I agree to the <a className="help-link" href={(import.meta.env.VITE_SITE_URL||'http://127.0.0.1:3000')+'/terms/'}>Terms</a> and acknowledge the <a className="help-link" href={(import.meta.env.VITE_SITE_URL||'http://127.0.0.1:3000')+'/privacy/'}>Privacy Policy</a>.</span></label>}
 {mode==='login'&&<a className="text-button" href="/forgot-password">Forgot your password?</a>}
 {action.error&&<ErrorNotice error={action.error}/>}
 {['verify-email','reset-password','accept-invite'].includes(mode)&&!token&&<InlineNote tone="warning">Open this page from the link in your email.</InlineNote>}
 <Button busy={action.isPending} disabled={['verify-email','reset-password','accept-invite'].includes(mode)&&!token} type="submit">{mode==='login'?'Sign in':mode==='signup'?'Create your account':mode==='forgot-password'?'Send reset link':mode==='reset-password'?'Save new password':mode==='verify-email'?'Verify email':'Accept invitation'}<ArrowRight size={15}/></Button>
 </form>}
 {!done&&<p className="auth-switch">{mode==='login'?<>New to Arc? <a href="/signup">Create an account</a></>:<>Already have an account? <a href="/login">Sign in</a></>}</p>}<div className="safety-text"><LockKeyhole size={12}/> Your password is never shared with connected applications.</div></Reveal><div className="auth-bottom">© {new Date().getFullYear()} Arc · <a href={(import.meta.env.VITE_SITE_URL||'http://127.0.0.1:3000')+'/security/'}>Security</a></div></main></div>
}
