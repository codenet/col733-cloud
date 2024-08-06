import glob
import logging
import os
import signal
import sys
import time
from threading import current_thread

from config import config
from worker import WcWorker
from mrds import MyRedis
from checkpoint import create_checkpoints

workers: list[WcWorker] = []
def sigterm_handler(signum, frame):
  logging.info('Killing main process!')
  for w in workers:
    w.kill()
  sys.exit()


if __name__ == "__main__":
  # Clear the log file
  open(config["LOGFILE"], 'w').close()
  logging.basicConfig(# filename=LOGFILE,
                      level=logging.DEBUG,
                      force=True,
                      format='%(asctime)s [%(threadName)s] %(levelname)s: %(message)s')
  thread = current_thread()
  thread.name = "client"
  logging.debug('Done setting up loggers.')

  rds = MyRedis()

  for file in glob.glob(config["DATA_PATH"]):
    rds.add_file(file)

  signal.signal(signal.SIGTERM, sigterm_handler)

  # Crash half the workers after they read a row
  for i in range(config["N_NORMAL_WORKERS"]):
    workers.append(WcWorker())

  for i in range(config["N_CRASHING_WORKERS"]):
    workers.append(WcWorker(crash=True))

  for i in range(config["N_SLEEPING_WORKERS"]):
    workers.append(WcWorker(slow=True))

  for w in workers:
    w.create_and_run(rds=rds)
  
  create_checkpoints(rds, config["CHECKPOINT_INTERVAL"])

  while rds.is_pending():
    time.sleep(2)
    rds.restart(downtime=config["REDIS_DOWNTIME"])

  logging.debug('Created all the workers')
  while True:
    try:
      pid_killed, status = os.wait()
      logging.info(f"Worker-{pid_killed} died with status {status}!")
    except:
      break

  for word, c in rds.top(3):
    logging.info(f"{word.decode()}: {c}")
