import threading,time,math
from foundation.errors.public import PublicError

# Every applicable bucket is checked BEFORE any bucket is consumed.
LUA='''
local now=tonumber(ARGV[1]);local count=#KEYS;local states={}
for i=1,count do
 local rate=tonumber(ARGV[2+i]);local raw=redis.call('HMGET',KEYS[i],'tokens','at')
 local tokens=tonumber(raw[1]) or rate;local at=tonumber(raw[2]) or now
 tokens=math.min(rate,tokens+math.max(0,now-at)*rate/60)
 if tokens<1 then return {0,math.ceil((1-tokens)*60/rate)} end
 states[i]={tokens-1,now}
end
for i=1,count do redis.call('HSET',KEYS[i],'tokens',states[i][1],'at',states[i][2]);redis.call('EXPIRE',KEYS[i],120) end
return {1,0}
'''
class Limiter:
    def __init__(self,settings):
        self.settings=settings;self.lock=threading.Lock();self.buckets={};self.redis=None
        if settings.redis_url:
            import redis
            self.redis=redis.Redis.from_url(settings.redis_url,socket_timeout=2,socket_connect_timeout=2)
    def check(self,keys_and_rates,clock=None):
        stamp=time.time() if clock is None else clock
        if self.redis:
            try:
                keys=[x[0] for x in keys_and_rates]
                result=self.redis.eval(LUA,len(keys),*keys,stamp,len(keys),*[x[1] for x in keys_and_rates])
            except Exception: raise PublicError('SERVICE_UNAVAILABLE')
            if not result[0]: raise PublicError('RATE_LIMITED',retry_after=int(result[1]))
            return
        if self.settings.env=='production': raise PublicError('SERVICE_UNAVAILABLE')
        with self.lock:
            next_values={}
            for key,rate in keys_and_rates:
                previous,at=self.buckets.get(key,(rate,stamp))
                remaining=min(rate,previous+max(0,stamp-at)*rate/60)
                if remaining<1: raise PublicError('RATE_LIMITED',retry_after=max(1,math.ceil((1-remaining)*60/rate)))
                next_values[key]=(remaining-1,stamp)
            self.buckets.update(next_values)
            if len(self.buckets)>10_000:
                self.buckets={k:v for k,v in self.buckets.items() if stamp-v[1]<180}

class StreamGate:
    """Expiring distributed connection slots; process-only substitute is development-only."""
    def __init__(self,limiter): self.limiter=limiter;self.lock=threading.Lock();self.local={}
    def acquire(self,key,identity,limit=5):
        stamp=time.time()
        if self.limiter.redis:
            script="""redis.call('ZREMRANGEBYSCORE',KEYS[1],'-inf',ARGV[1]);if redis.call('ZCARD',KEYS[1])>=tonumber(ARGV[3]) then return 0 end;redis.call('ZADD',KEYS[1],ARGV[2],ARGV[4]);redis.call('EXPIRE',KEYS[1],90);return 1"""
            try: permitted=self.limiter.redis.eval(script,1,key,stamp,stamp+60,limit,identity)
            except Exception: raise PublicError('SERVICE_UNAVAILABLE')
            if not permitted: raise PublicError('CAPACITY_REACHED')
        else:
            with self.lock:
                values={k:v for k,v in self.local.get(key,{}).items() if v>stamp}
                if len(values)>=limit: raise PublicError('CAPACITY_REACHED')
                values[identity]=stamp+60;self.local[key]=values
    def renew(self,key,identity):
        if self.limiter.redis:
            try:
                updated=self.limiter.redis.zadd(key,{identity:time.time()+60},xx=True)
                self.limiter.redis.expire(key,90)
            except Exception: raise PublicError('SERVICE_UNAVAILABLE')
        else:
            with self.lock:
                if identity not in self.local.get(key,{}): raise PublicError('CAPACITY_REACHED')
                self.local[key][identity]=time.time()+60
    def release(self,key,identity):
        try:
            if self.limiter.redis: self.limiter.redis.zrem(key,identity)
            else:
                with self.lock: self.local.get(key,{}).pop(identity,None)
        except Exception: pass  # Slot expires; never mask an already delivered response.
