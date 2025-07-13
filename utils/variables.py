import pytz
import datetime
import time


SGT = pytz.timezone('Asia/Singapore')
START_TIME = time.time()
last_update = datetime.datetime.now(SGT)
currently_playing = {}
audio = None