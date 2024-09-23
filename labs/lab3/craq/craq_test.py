import threading
import unittest
import os
import time

from craq.craq_cluster import CraqCluster, CraqClient
from core.logger import client_logger
from core.logger import set_client_logfile, remove_client_logfile

class TestCRAQ(unittest.TestCase):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.craq = CraqCluster()

  def setUp(self) -> None:
    self.craq.start_all()

  def tearDown(self) -> None:
    self.craq.stop_all()


  def test_gen_history(self) -> None:
    # Redirect the logs to a file
    logfile_name = f"logs/{self._testMethodName}.log"
    if os.path.exists(logfile_name):
      os.remove(logfile_name)
    file_sink_id = set_client_logfile(logfile_name)

    def setter(c: CraqClient, iters: int, name: str) -> None:
      logger = client_logger.bind(server_name=name)
      for i in range(iters):
        logger.info(f"Setting key = {i}")
        c.set("key", f"{i}")
        logger.info(f"Set key = {i}")

    def getter(c: CraqClient, iters: int, name: str) -> None:
      logger = client_logger.bind(server_name=name)
      for _ in range(iters):
        logger.info(f"Getting key")
        status, val = c.get("key")
        self.assertTrue(status, msg=val)
        logger.info(f"Get key = {val}")

    try:
      client1 = self.craq.connect()
      client2 = self.craq.connect()

      client1.set("key", "0")
      s = threading.Thread(target=setter, args=(client1, 10, "worker_0"))
      g = threading.Thread(target=getter, args=(client2, 10, "worker_1"))
      s.start()
      g.start()
      s.join()
      g.join()
    finally:
      remove_client_logfile(file_sink_id)

if __name__ == "__main__":
  unittest.main()
