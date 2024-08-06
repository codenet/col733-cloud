from __future__ import annotations

import logging
import os
import signal
import sys
from abc import abstractmethod, ABC
from threading import current_thread
from typing import Any, Final
from multiprocessing import Process


class Worker(ABC):
  GROUP: Final = "worker"

  def __init__(self, **kwargs: Any):
    self.name = "worker-?"
    self.pid = -1
    self.crash = kwargs['crash'] if 'crash' in kwargs else False
    self.slow = kwargs['slow'] if 'slow' in kwargs else False

  def create_and_run(self, **kwargs: Any) -> None:
    # Create a process using the multiprocessing library and set self.pid
    raise NotImplementedError

  @abstractmethod
  def run(self, **kwargs: Any) -> None:
    raise NotImplementedError

  def kill(self) -> None:
    logging.info(f"Killing {self.name}")
    os.kill(self.pid, signal.SIGKILL)
