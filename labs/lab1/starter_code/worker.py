import logging
import sys
import time
from typing import Any

from base import Worker
from config import config
from mrds import MyRedis


class WcWorker(Worker):
  def run(self, **kwargs: Any) -> None:
    rds: MyRedis = kwargs['rds']

    # Write the code for the worker thread here.
    while True:
      # Read

      if self.crash:
        # DO NOT MODIFY THIS!!!
        logging.critical(f"CRASHING!")
        sys.exit()

      if self.slow:
        # DO NOT MODIFY THIS!!!
        logging.critical(f"Sleeping!")
        time.sleep(1)

      # Process here

    logging.info("Exiting")
