from gevent import monkey; monkey.patch_all()
from gevent.pywsgi import WSGIServer
import time
from urllib.parse import urlparse
import flask, requests

app = flask.Flask(__name__)

def copy_response(r):
	ret = flask.Response(r.text)
	v = r.headers.get("Content-Type")
	if v:
		ret.headers["Content-Type"] = v
	return ret

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

@app.get('/groups/1633743/items')
def reply():
	url = urlparse(flask.request.url)
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
		# Must be noted that zotero servers return 500 and no request
		# delay when the server is overloaded, thus we retry several
		# times even if no request delay is given.
		if wait <= 0:
			wait = 5
		time.sleep(wait)
	raise Exception(repr((r.headers, r.text)))

if __name__ == "__main__":
	server = WSGIServer(("0.0.0.0", 8024), app)
	server.serve_forever()
