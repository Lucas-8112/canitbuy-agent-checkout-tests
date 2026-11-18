# One Skyvern run (local mode) against the test store. Task text and store address come from runner.py.
import asyncio, json, os, sys, time, urllib.error, urllib.request
sys.path.insert(0, '/vercel/pilot')
from runner import TASKS, GUARD, get, BASE, PORT
MAX_STEPS = int(os.environ.get('MAX_STEPS', '40'))


async def one(rid, kind, cond, model, arm):
    try:
        urllib.request.urlopen(f'{BASE}/_start/{rid}?k={kind}&cond={cond}', timeout=20).read()
    except urllib.error.HTTPError:
        pass
    assert get(f'/_state/{rid}')['cond'] == cond
    url = f'http://{rid}.nordlys-shop.test' + ('' if PORT == '80' else f':{PORT}')
    task = TASKS[kind].format(url=url) + ('\n\n' + GUARD if arm == 'guard' else '')
    os.environ.update(ENABLE_OPENAI_COMPATIBLE='true', OPENAI_COMPATIBLE_MODEL_NAME=model, OPENAI_COMPATIBLE_API_KEY='pilot',
                      OPENAI_COMPATIBLE_API_BASE=f'{BASE}/llm/{rid}/v1', OPENAI_COMPATIBLE_SUPPORTS_VISION='true',
                      LLM_KEY='OPENAI_COMPATIBLE', SKYVERN_TELEMETRY='false', BROWSER_TYPE='chromium-headless')
    from importlib.metadata import version
    from skyvern import Skyvern
    rec = {'id': rid, 'kind': kind, 'cond': cond, 'model': model, 'arm': arm, 'program': 'skyvern ' + version('skyvern'),
           'max_steps': MAX_STEPS, 'at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
    t0 = time.time()
    try:
        sk = Skyvern.local(use_in_memory_db=True, settings={'BROWSER_TYPE': 'chromium-headless', 'SKYVERN_TELEMETRY': False})
        res = await sk.run_task(prompt=task, url=url, max_steps=MAX_STEPS, wait_for_completion=True, timeout=600)
        d = res.model_dump(mode='json') if hasattr(res, 'model_dump') else dict(res)
        rec.update(status=str(d.get('status')), text=json.dumps(d.get('output'))[:4000] if d.get('output') is not None else '',
                   error=d.get('failure_reason'), steps=d.get('step_count'),
                   raw={k: v for k, v in d.items() if k in ('run_id', 'status', 'failure_reason', 'step_count', 'errors', 'downloaded_files', 'app_url')})
    except Exception as e:
        rec.update(status='crash', error=repr(e)[:800])
    rec['secs'] = round(time.time() - t0, 1)
    try:
        st = get(f'/_state/{rid}')
        rec.update(state=st['state'], paths=st['paths'], llm=st['llm'])
    except Exception as e:
        rec['state_error'] = repr(e)[:200]
    return rec


if __name__ == '__main__':
    rec = asyncio.run(one(*sys.argv[1:6]))
    open(sys.argv[6], 'a').write(json.dumps(rec, default=str) + '\n')
    os._exit(0)
