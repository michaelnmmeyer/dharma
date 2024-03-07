from gevent import monkey; monkey.patch_all()
import time
from urllib.parse import urlparse
import bottle, requests

def copy_response(r):
    v = r.headers.get("Content-Type")
    if v:
        bottle.response.set_header("Content-Type", v)
    return r.text

def next_request_delay(r):
    wait = -1
    n = r.headers.get("Backoff", "")
    if n.isdigit():
        wait = max(wait, int(n))
    n = r.headers.get("Retry-After", "")
    if n.isdigit():
        wait = max(wait, int(n))
    return wait

MY_API_KEY = "ojTBU4SxEQ4L0OqUhFVyImjq"

@bottle.route('/groups/1633743/items')
def reply():
    url = urlparse(bottle.request.url)
    url = url._replace(scheme="https", netloc="api.zotero.org")
    url = url.geturl()
    s = requests.Session()
    s.headers["Zotero-API-Version"] = "3"
    s.headers["Zotero-API-Key"] = MY_API_KEY
    for i in range(5):
        r = s.get(url)
        if r.ok:
            return copy_response(r)
        wait = next_request_delay(r)
        if wait < 0:
            wait = 5
        time.sleep(wait)
    raise Exception(repr((r.headers, r.text)))

bottle.run(host='0.0.0.0', port=8024, server='gevent', reloader=True)
