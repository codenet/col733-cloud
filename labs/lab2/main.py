import glob
import os
import signal
import time
import argparse
from enum import Enum

from constants import STREAMS, NUM_MAPPERS, MAPPER_PORTS, REDUCER_PORTS
from _coordinator import Coordinator
from mrds import MyRedis
from mylog import Logger

logging = Logger().get_logger()


if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument(
      "recovery_test_mode",
      type=Coordinator.RecoveryTestModes,
      choices=list(Coordinator.RecoveryTestModes),
  )
  opts = parser.parse_args()

  Logger()
  rds = MyRedis()
  pattern = "csv_files/*.csv"

  j: int = 1
  for file in glob.glob(pattern):
      rds.add_file(STREAMS[j % NUM_MAPPERS], file, j)
      j += 1
  
  C = Coordinator(opts.recovery_test_mode)
  C.start()
  C.join()
