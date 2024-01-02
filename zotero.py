# Syncing with zotero servers. This must be run in a separate process.
# The relevant documentation is at:
# https://www.zotero.org/support/dev/web_api/v3/streaming_api

import logging, json, traceback
from websockets.sync.client import connect # https://websockets.readthedocs.io
from dharma import config, change

create_subscriptions = config.json_adapter({
   "action": "createSubscriptions",
   "subscriptions": [
      {
         "apiKey": "ojTBU4SxEQ4L0OqUhFVyImjq",
	 "topics": ["/groups/1633743", "/groups/5336269"]
      }
   ]
})
# Response:
# {"event":"","subscriptions":[{"apiKey":"ojTBU4SxEQ4L0OqUhFVyImjq","topics":["/groups/1633743","/groups/5336269"]}],"errors":[]}

# After an update we receive:
# {"event":"topicUpdated","topic":"/groups/5336269","version":6}

delete_subscriptions = config.json_adapter({
    "action": "deleteSubscriptions",
    "subscriptions": [
        {
            "apiKey": "ojTBU4SxEQ4L0OqUhFVyImjq"
        }
    ]
})
# Response:
# {"event":"subscriptionsDeleted","subscriptions":[{"apiKey":"ojTBU4SxEQ4L0OqUhFVyImjq","topics":["/groups/1633743","/groups/5336269"]}]}

def read_message(sock):
	ret = sock.recv()
	logging.info(ret)
	return json.loads(ret)

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
			# {"event": "connected", "retry": 10000}
			assert ret["event"] == "connected"
			main(sock)
		except KeyboardInterrupt:
			exit = True
		except Exception as e:
			logging.error(e)
			traceback.print_exception(e)
		finally:
			sock.close()
	logging.info("exiting")
