# Syncing with zotero servers. This must be run in a separate process.
# The relevant documentation is at:
# https://www.zotero.org/support/dev/web_api/v3/streaming_api

import logging, traceback
from websockets.sync.client import connect # https://websockets.readthedocs.io
from dharma import config, change, biblio

create_subscriptions = config.to_json({
	"action": "createSubscriptions",
	"subscriptions": [{
		"apiKey": biblio.MY_API_KEY,
		"topics": [f"/groups/{biblio.LIBRARY_ID}", "/groups/5336269"]
	}]
})
# Response:
# {"event":"","subscriptions":[{"apiKey":"ojTBU4SxEQ4L0OqUhFVyImjq","topics":["/groups/1633743","/groups/5336269"]}],"errors":[]}

# After an update we receive:
# {"event":"topicUpdated","topic":"/groups/5336269","version":6}

delete_subscriptions = config.to_json({
	"action": "deleteSubscriptions",
	"subscriptions": [{"apiKey": MY_API_KEY}]
})
# Response:
# {"event":"subscriptionsDeleted","subscriptions":[{"apiKey":"ojTBU4SxEQ4L0OqUhFVyImjq","topics":["/groups/1633743","/groups/5336269"]}]}

def read_message(sock):
	ret = sock.recv()
	logging.info(ret)
	return config.from_json(ret)

def main(sock):
	sock.send(create_subscriptions)
	ret = read_message(sock)
	assert ret["event"] == "subscriptionsCreated"
	while True:
		ret = read_message(sock)
		assert ret["event"] in ("topicUpdated", "topicAdded", "topicRemoved")
		change.notify("bib")

if __name__ == "__main__":
	exit = False
	while not exit:
		sock = connect("wss://stream.zotero.org")
		try:
			ret = read_message(sock)
			# Should receive {"event": "connected", "retry": 10000}
			assert ret["event"] == "connected"
			logging.info("connected")
			main(sock)
		except KeyboardInterrupt:
			exit = True
		finally:
			sock.close()
	logging.info("exiting")
