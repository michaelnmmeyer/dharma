from gevent import monkey; monkey.patch_all()
import time
from urllib.parse import urlparse
import bottle, requests

def copy_response(r):
    v = r.headers.get("Content-Type")
    if v:
        bottle.response.set_header("Content-Type", v)
    return r.text

@bottle.route('/groups/1633743/items')
def reply():
    url = urlparse(bottle.request.url)
    url = url._replace(scheme="https", netloc="api.zotero.org")
    url = url.geturl()
    print(url)
    while True:
        r = requests.get(url)
        if r.ok:
            return copy_response(r)
        if r.status_code != 500:
            raise Exception
        time.sleep(5)

bottle.run(host='0.0.0.0', port=8024, server='gevent', reloader=True)
