"""Create LOCAL secrets. Does not enable live services or weaken production gates."""
from pathlib import Path
import secrets,os
from cryptography.fernet import Fernet
ROOT=Path(__file__).resolve().parents[1]
path=ROOT/'.env'
if path.exists(): raise SystemExit('.env exists; it was not overwritten.')
text=(ROOT/'.env.example').read_text()
text=text.replace('ARC_SECRET_KEY=\n','ARC_SECRET_KEY='+secrets.token_urlsafe(48)+'\n')
text=text.replace('ARC_ENCRYPTION_KEY=\n','ARC_ENCRYPTION_KEY='+Fernet.generate_key().decode()+'\n')
path.write_text(text);path.chmod(0o600)
(ROOT/'.local').mkdir(exist_ok=True)
print('Created local .env with new random keys. Next: run arc-foundation migrate.')
