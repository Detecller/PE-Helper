import pytz
import datetime
import time


SGT = pytz.timezone('Asia/Singapore')
PT = pytz.timezone('America/Los_Angeles')
START_TIME = time.time()
last_update = datetime.datetime.now(SGT)
currently_playing = {}
audio = None