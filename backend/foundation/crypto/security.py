"""Small security primitives with deterministic tests; no home-grown encryption."""
import base64, hashlib, hmac, ipaddress, json, re, secrets, socket, struct, time
from urllib.parse import urlsplit
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError
from cryptography.fernet import Fernet, InvalidToken
from foundation.errors.public import PublicError

PASSWORDS=PasswordHasher(time_cost=2,memory_cost=19456,parallelism=1)
DUMMY_HASH=PASSWORDS.hash(secrets.token_urlsafe(32))

def password_hash(password):
    if len(password)<12 or len(password)>128: raise PublicError('INVALID_INPUT')
    return PASSWORDS.hash(password)

def password_matches(stored,password):
    try: return PASSWORDS.verify(stored or DUMMY_HASH,password)
    except (VerifyMismatchError,VerificationError,InvalidHashError): return False

def digest(value): return hashlib.sha256(value.encode()).hexdigest()
def keyed_digest(value,secret): return hmac.new(secret.encode(),value.encode(),hashlib.sha256).hexdigest()
def token(): return secrets.token_urlsafe(32)

def seal(value,settings,purpose):
    return Fernet(settings.encryption_key.encode()).encrypt((purpose+'\0'+value).encode()).decode()

def unseal(value,settings,purpose):
    try:
        plain=Fernet(settings.encryption_key.encode()).decrypt(value.encode()).decode()
        if not plain.startswith(purpose+'\0'): raise ValueError('context')
        return plain.split('\0',1)[1]
    except (InvalidToken,ValueError,UnicodeError): raise PublicError('SERVICE_UNAVAILABLE')

def signed_token(payload,settings):
    body=base64.urlsafe_b64encode(json.dumps(payload,separators=(',',':')).encode()).rstrip(b'=').decode()
    return body+'.'+keyed_digest(body,settings.secret_key)

def verify_signed(value,settings,purpose):
    try:
        body,signature=value.split('.',1)
        if not hmac.compare_digest(signature,keyed_digest(body,settings.secret_key)): raise ValueError()
        data=json.loads(base64.urlsafe_b64decode(body+'='*(-len(body)%4)))
        if data.get('purpose')!=purpose or int(data.get('exp',0))<time.time(): raise ValueError()
        return data
    except (ValueError,TypeError,KeyError,UnicodeError): raise PublicError('INVALID_TOKEN')

def csrf_token(settings,audience,session_cookie):
    return signed_token({'purpose':'csrf','aud':audience,'sid':digest(session_cookie or ''),'exp':int(time.time())+3600},settings)

def check_csrf(request,settings,audience):
    supplied=request.headers.get('x-csrf-token','')
    cookie=request.cookies.get(settings.cookie(audience,'csrf'),'')
    if not supplied or not hmac.compare_digest(supplied,cookie): raise PublicError('CSRF_FAILED')
    try: data=verify_signed(supplied,settings,'csrf')
    except PublicError: raise PublicError('CSRF_FAILED')
    sid=digest(request.cookies.get(settings.cookie(audience),'') or '')
    if data.get('aud')!=audience or not hmac.compare_digest(data.get('sid',''),sid): raise PublicError('CSRF_FAILED')

def totp_code(secret,at=None,digits=6,period=30):
    key=base64.b32decode(secret.upper()+'='*(-len(secret)%8))
    counter=int((time.time() if at is None else at)//period)
    value=hmac.new(key,struct.pack('>Q',counter),hashlib.sha1).digest()
    offset=value[-1]&15
    return str((struct.unpack('>I',value[offset:offset+4])[0]&0x7fffffff)%(10**digits)).zfill(digits)

def totp_step(secret,code,last=-1,at=None):
    stamp=time.time() if at is None else at
    if not re.fullmatch(r'\d{6}',code): return None
    for step in (int(stamp//30),int(stamp//30)-1,int(stamp//30)+1):
        if step>last and hmac.compare_digest(totp_code(secret,step*30),code): return step
    return None

def validate_webhook_url(url,allow_local=False,resolver=socket.getaddrinfo):
    try:
        parts=urlsplit(url)
        if parts.scheme!='https' or not parts.hostname or parts.username or parts.password or parts.fragment:
            raise ValueError()
        if parts.port not in (None,443): raise ValueError()
        addresses={result[4][0] for result in resolver(parts.hostname,443,type=socket.SOCK_STREAM)}
        if not addresses: raise ValueError()
        for address in addresses:
            if not allow_local and not ipaddress.ip_address(address).is_global: raise ValueError()
        return parts,sorted(addresses)
    except (ValueError,OSError,UnicodeError): raise PublicError('WEBHOOK_BLOCKED')

def webhook_signature(secret,body,timestamp):
    return 't='+str(timestamp)+',v1='+hmac.new(secret.encode(),str(timestamp).encode()+b'.'+body,hashlib.sha256).hexdigest()

def redact_support(text):
    text=re.sub(r'(?i)(Bearer\s+)[A-Za-z0-9_\-\.]+',r'\1[REDACTED]',text)
    text=re.sub(r'\b(?:arc_(?:test|live)_|sk_(?:test|live)_|whsec_)[A-Za-z0-9_\-]+','[REDACTED]',text)
    return text
