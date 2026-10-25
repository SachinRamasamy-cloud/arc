import json,subprocess,os,signal,sys,hashlib
from pathlib import Path
from foundation.errors.public import PublicError

def run_native(settings,request):
    executable=Path(settings.native_path).resolve()
    if not executable.is_file(): raise PublicError('SERVICE_UNAVAILABLE')
    # A fresh child sets process limits before exec; never use preexec_fn in a web-server thread.
    launcher=Path(__file__).with_name('sandbox_exec.py')
    process=subprocess.Popen([sys.executable,"-I","-S",str(launcher),str(executable)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8'},start_new_session=True)
    try:
        output,_=process.communicate(json.dumps(request,ensure_ascii=False,allow_nan=False).encode(),timeout=settings.worker_timeout_seconds)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid,signal.SIGKILL);process.communicate()
        raise PublicError('PROCESSING_TIMEOUT')
    if len(output)>16_000_000: raise PublicError('PROCESSING_FAILED')
    try: value=json.loads(output)
    except (ValueError,UnicodeError): raise PublicError('PROCESSING_FAILED')
    if process.returncode!=0 or value.get('ok') is not True: raise PublicError('INVALID_INPUT')
    if set(value)-{'ok','engine_version','records','format','output'}: raise PublicError('PROCESSING_FAILED')
    return value
