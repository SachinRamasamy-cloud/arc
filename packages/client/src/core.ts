export const safeMessages: Record<string, string> = {
  UNAUTHORIZED: 'Your session has ended. Please sign in again.',
  INVALID_CREDENTIALS: 'The email or password could not be verified.',
  EMAIL_UNVERIFIED: 'Verify your email address before signing in.',
  MFA_REQUIRED: 'Enter an authenticator or recovery code to continue.',
  INVALID_CODE: 'The code is invalid, expired, or already used.',
  FORBIDDEN: 'You do not have permission for this action.',
  NOT_FOUND: 'This resource is not available.',
  INVALID_INPUT: 'Check the highlighted input and try again.',
  INVALID_TOKEN: 'This link is invalid, expired, or already used.',
  CSRF_FAILED: 'Reload this page to refresh your security session.',
  ORIGIN_BLOCKED: 'This connection is not allowed.',
  RATE_LIMITED: 'Too many requests. Wait a moment before trying again.',
  CAPACITY_REACHED: 'Your processing capacity is currently in use.',
  INSUFFICIENT_CREDITS: 'There are not enough available credits for this request.',
  BUDGET_EXCEEDED: 'This request would exceed your configured budget.',
  POLICY_LIMIT: 'This value exceeds your available allowance.',
  LIVE_UNAVAILABLE: 'Live access is not enabled. Continue in the test environment.',
  INTEGRATION_UNAVAILABLE: 'This service has not been configured yet.',
  SERVICE_UNAVAILABLE: 'This service is temporarily unavailable.',
  CONFLICT: 'This action conflicts with the current state. Refresh and try again.',
  STALE_DRAFT: 'Someone saved newer changes. Reload before saving again.',
  WORKFLOW_INVALID: 'Check your workflow connections and operation settings.',
  UPLOAD_NOT_READY: 'Complete and verify the upload before using this file.',
  PAYLOAD_TOO_LARGE: 'The input exceeds the supported size limit.',
  PROCESSING_FAILED: 'The input could not be processed.',
  PROCESSING_TIMEOUT: 'This operation exceeded its processing time limit.',
  NETWORK_ERROR: 'The connection was interrupted. Check your network and retry.',
  EVENT_CURSOR_EXPIRED: 'Refresh the execution details before reconnecting.',
  WEBHOOK_BLOCKED: 'Use an approved public HTTPS endpoint.',
  UNSUPPORTED_OPERATION: 'This operation or file format is not supported.',
  UPLOAD_FAILED: 'The upload did not complete. Check your connection and retry.',
  INTERNAL_ERROR: 'Something went wrong. Use the request reference to contact support.'
};
export class ApiError extends Error {
  constructor(public code: string, public status = 0, public requestId = '', public fields: {field:string;message:string}[] = []) {
    super(safeMessages[code] || safeMessages.INTERNAL_ERROR); this.name = 'ApiError';
  }
}
export function normalizeError(body: unknown, status: number): ApiError {
  const value = body && typeof body === 'object' ? body as Record<string, unknown> : {};
  const code = typeof value.code === 'string' && safeMessages[value.code] ? value.code : 'INTERNAL_ERROR';
  const requestId = typeof value.request_id === 'string' && /^req_[a-f0-9]{32}$/.test(value.request_id) ? value.request_id : '';
  const fields = Array.isArray(value.fields) ? value.fields.slice(0,16).filter((v):v is {field:string;message:string} => typeof v?.field==='string').map(v=>({field:v.field.slice(0,120),message:'Check this value.'})) : [];
  return new ApiError(code, status, requestId, fields);
}
export function credits(value: number): string {
  if (!Number.isFinite(value)) return '—';
  return new Intl.NumberFormat('en-US', {maximumFractionDigits:3}).format(value / 1000);
}
export function bytes(value: number): string {
  if (!Number.isFinite(value) || value < 0) return '—';
  if (value < 1024) return value + ' B';
  const unit = Math.min(3, Math.floor(Math.log(value)/Math.log(1024)));
  return (value/1024**unit).toFixed(1) + ' ' + ['B','KB','MB','GB'][unit];
}
export function dateTime(seconds?: number | null): string {
  return seconds ? new Date(seconds*1000).toLocaleString(undefined,{dateStyle:'medium',timeStyle:'short'}) : '—';
}
export function parseData(value: string, operation: string): unknown {
  if (operation === 'csv_to_json') return value;
  try { return JSON.parse(value); } catch { throw new ApiError('INVALID_INPUT',422); }
}
export type RunEvent = {id:number;type:string;data:Record<string,unknown>};
export function appendEvent(events:RunEvent[], event:RunEvent, limit=200):RunEvent[] {
  if (events.some(e=>e.id===event.id)) return events;
  return [...events,event].sort((a,b)=>a.id-b.id).slice(-limit);
}
export function allowed(role:string, permission:string):boolean {
  const roles:Record<string,string[]>={owner:['read','build','keys','files','finance','team','security','privacy'],admin:['read','build','keys','files','finance','team','security','privacy'],developer:['read','build','keys','files'],billing:['read','finance'],viewer:['read']};
  return !!roles[role]?.includes(permission);
}

/** Display-only values: the server remains the accounting authority. */
export function moneyMinor(amount: number, currency: string): string {
  if (!Number.isSafeInteger(amount) || !['usd','eur','gbp','inr'].includes(currency.toLowerCase())) return '—';
  return new Intl.NumberFormat('en-US', {style:'currency',currency:currency.toUpperCase()}).format(amount / 100);
}
export function billingFigures(data: any, environment: 'test'|'live') {
  const wallet = data?.wallets?.find((item: any)=>item.environment===environment);
  return {
    available:wallet?.available_milli ?? 0,
    reserved:(wallet?.reserved_milli ?? 0)+(environment==='live' ? data?.included_reserved_milli ?? 0 : 0),
    allowance:environment==='live' ? data?.included_available_milli ?? 0 : 0,
    usage:data?.usage?.gross_milli ?? 0,
    included:data?.usage?.included_milli ?? 0,
    prepaid:data?.usage?.prepaid_milli ?? 0,
  };
}
export function paymentDestination(url: unknown): string {
  if (typeof url !== 'string') throw new ApiError('SERVICE_UNAVAILABLE',503);
  const parsed=new URL(url);
  if(parsed.protocol!=='https:' || !['checkout.stripe.com','billing.stripe.com'].includes(parsed.hostname) || parsed.username || parsed.password) throw new ApiError('SERVICE_UNAVAILABLE',503);
  return parsed.href;
}
