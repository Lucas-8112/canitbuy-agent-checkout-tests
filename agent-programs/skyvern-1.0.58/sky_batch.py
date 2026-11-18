import json, os, subprocess, sys, time, urllib.request
BASE = os.environ['PILOT_BASE']; out = sys.argv[2]; par = int(sys.argv[3]); STOP = float(os.environ.get('STOP_USD', '20'))
todo = json.load(open(sys.argv[1]))
done = {json.loads(l)['id'] for l in open(out) if l.strip()} if os.path.exists(out) else set()
todo = [r for r in todo if r['id'] not in done]; running = []; os.makedirs('logs', exist_ok=True)
spend = lambda: json.loads(urllib.request.urlopen(BASE + '/_spend', timeout=20).read())['total']
while todo or running:
    while todo and len(running) < par:
        if spend() >= STOP: print('STOP: spend limit', flush=True); todo = []; break
        r = todo.pop(0)
        p = subprocess.Popen(['/vercel/sky/.venv/bin/python', '/vercel/sky/sky_runner.py', r['id'], r['kind'], r['cond'], r['model'], r['arm'], out],
                             stdout=subprocess.DEVNULL, stderr=open(f'logs/{r["id"]}.log', 'w'))
        running.append((p, r, time.time()))
    time.sleep(2)
    for item in list(running):
        p, r, t = item
        if p.poll() is not None:
            running.remove(item); print('done', r['id'], p.returncode, round(time.time() - t), flush=True)
            if p.returncode != 0 and r['id'] not in open(out).read(): open(out, 'a').write(json.dumps({**r, 'status': 'crash', 'error': 'exit %s' % p.returncode}) + '\n')
        elif time.time() - t > 840:
            p.kill(); running.remove(item)
            open(out, 'a').write(json.dumps({**r, 'status': 'killed', 'secs': round(time.time() - t)}) + '\n'); print('killed', r['id'], flush=True)
print('BATCH DONE', flush=True)
