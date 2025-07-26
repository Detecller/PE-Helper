import os
import json


TRACKER_FILE = "../data/last_seen_ids.json"


def load_last_seen_ids():
	if not os.path.exists(TRACKER_FILE):
		return {}
	with open(TRACKER_FILE, "r") as f:
		return json.load(f)


def save_last_seen_ids(last_seen_ids):
	with open(TRACKER_FILE, "w") as f:
		json.dump(last_seen_ids, f)