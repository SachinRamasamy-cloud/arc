"""Configuration. Production is fail-closed until deployment evidence is supplied."""
from pathlib import Path
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_MODULE_PATH = Path(__file__).resolve()
_SOURCE_ROOT = _MODULE_PATH.parents[3]
# Editable installs use the checkout's .env; installed wheels use the working directory.
ROOT = _SOURCE_ROOT if _MODULE_PATH == _SOURCE_ROOT / 'backend/foundation/config/settings.py' else Path.cwd()

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='ARC_', env_file=str(ROOT / '.env'), extra='ignore')
    env: str = 'development'
    database_url: str = 'sqlite:///./.local/arc.sqlite'
    secret_key: str = ''
    encryption_key: str = ''
    api_origin: str = 'http://127.0.0.1:8000'
    portal_origin: str = 'http://127.0.0.1:5173'
    operator_origin: str = 'http://127.0.0.1:5174'
    site_origin: str = 'http://127.0.0.1:3000'
    storage_mode: str = 'local'
    storage_dir: str = '.local/objects'
    mail_mode: str = 'local'
    native_path: str = 'native/build/arc-engine'
    redis_url: str = ''
    r2_endpoint: str = ''
    r2_bucket: str = ''
    r2_access_key: str = ''
    r2_secret_key: str = ''
    stripe_secret_key: str = ''
    stripe_webhook_secret: str = ''
    stripe_credit_price_id: str = ''
    stripe_plan_price_id: str = ''
    stripe_credit_pack_milli: int = 100_000
    stripe_credit_pack_minor: int = 1000
    stripe_plan_minor: int = 2900
    stripe_plan_allowance_milli: int = 300_000
    currency: str = 'usd'
    # Every billed operation snapshots these settings. Replace dev prices before live use.
    price_version: str = 'development-2'
    processing_base_milli: int = 500
    processing_kib_milli: int = 100
    records_per_1000_milli: int = 1000
    storage_gb_month_milli: int = 1000
    storage_quota_bytes: int = 256_000_000
    records_quota_bytes: int = 16_000_000
    records_quota_count: int = 10_000
    record_max_bytes: int = 65_536
    receipt_quota_bytes: int = 64_000_000
    receipt_quota_count: int = 4096
    live_enabled: bool = False
    legal_approved: bool = False
    pricing_approved: bool = False
    security_qualified: bool = False
    backup_qualified: bool = False
    smtp_host: str = ''
    smtp_port: int = 587
    smtp_user: str = ''
    smtp_password: str = ''
    mail_from: str = ''
    max_body_bytes: int = 2_000_000
    max_file_bytes: int = 16_000_000
    session_seconds: int = 28_800
    worker_timeout_seconds: int = 20
    job_lease_seconds: int = 90
    allow_local_webhooks: bool = False

    @model_validator(mode='after')
    def validate_security(self):
        if len(self.secret_key) < 32:
            raise ValueError('ARC_SECRET_KEY must be randomly generated (at least 32 characters). Run scripts/bootstrap.py.')
        from cryptography.fernet import Fernet
        try:
            Fernet(self.encryption_key.encode())
        except Exception as exc:
            raise ValueError('ARC_ENCRYPTION_KEY must be a generated Fernet key.') from exc
        if min(self.processing_base_milli, self.processing_kib_milli, self.records_per_1000_milli, self.storage_gb_month_milli) < 0:
            raise ValueError('Billing rates must be nonnegative')
        if self.currency not in ('usd','eur','gbp','inr'):
            raise ValueError('This release supports USD, EUR, GBP and INR minor units only')
        if not self.price_version or len(self.price_version) > 64:
            raise ValueError('A bounded price version is required')
        if self.env not in {'development', 'test', 'production'}:
            raise ValueError('Unknown environment')
        if self.env == 'production':
            missing = []
            if not self.database_url.startswith('postgresql'): missing.append('PostgreSQL')
            if not self.redis_url: missing.append('Redis')
            if self.storage_mode != 'r2': missing.append('private R2')
            if self.mail_mode != 'smtp' or not self.smtp_host or not self.mail_from: missing.append('transactional mail')
            for name in ('api_origin', 'portal_origin', 'operator_origin', 'site_origin'):
                if not getattr(self, name).startswith('https://'): missing.append(name + ' HTTPS')
            if self.allow_local_webhooks: missing.append('disable local webhooks')
            if not self.security_qualified: missing.append('security qualification')
            if not self.backup_qualified: missing.append('restore qualification')
            if not self.legal_approved: missing.append('approved legal documents')
            if self.live_enabled and self.price_version.startswith('development'):
                missing.append('published price version')
            if self.live_enabled and not (self.pricing_approved and self.stripe_secret_key and self.stripe_webhook_secret):
                missing.append('approved pricing and verified Stripe configuration')
            if missing: raise ValueError('Production blocked: ' + ', '.join(missing))
        if self.storage_mode == 'r2' and not all((self.r2_endpoint, self.r2_bucket, self.r2_access_key, self.r2_secret_key)):
            raise ValueError('R2 storage requires all private bucket credentials')
        return self

    @property
    def secure_cookies(self): return self.env == 'production'

    def cookie(self, audience: str, kind: str = 'session') -> str:
        return ('__Host-' if self.secure_cookies else '') + f'arc_{audience}_{kind}'
