from multiprocessing import Process
from coordinator import CoordinatorState, PHASE, WorkerState, SendThread, RecvThread
import queue
from enum import Enum
import random
import time
import socket
import os

from constants import NUM_MAPPERS, NUM_REDUCERS, \
  MAPPER_PORTS, REDUCER_PORTS, COORDINATOR_PORT

from mylog import Logger
logging = Logger().get_logger()


# ###################################################################################
# ################################### DO NOT CHANGE #################################
# ###################################################################################
class Coordinator(Process):
  class RecoveryTestModes(Enum):
    TEST_NONE = 'none'
    TEST_MAPPER = 'test_mapper'
    TEST_REDUCER = 'test_reducer'
    TEST_BOTH = 'test_both'
    TEST_ALL = 'test_all'

    def __str__(self) -> str:
      return self.value

  def __init__(self, test_mode: RecoveryTestModes) -> None:
    super().__init__()
    self.global_state = CoordinatorState()
    self.phase_queue: queue.Queue[PHASE]
    self._recovery_test_mode = test_mode

    for i, mp in enumerate(MAPPER_PORTS):
      m = WorkerState(i, True, ("localhost", mp))
      self.global_state.workers[m.id] = m

    for i, rp in enumerate(REDUCER_PORTS):
      r = WorkerState(i, False, ("localhost", rp))
      self.global_state.workers[r.id] = r

  def initialize_workers(self):
    # start reducers
    for _, ws in self.global_state.workers.items():
      if not ws.is_mapper:
        ws.start_worker()

    time.sleep(2)

    # start mappers
    for _, ws in self.global_state.workers.items():
      if ws.is_mapper:
        ws.start_worker()

  def kill_worker(self, id: str):
    for w in self.global_state.workers.values():
      if w.id == id:
        w.process.kill()
        logging.critical(f"Killing {w.id}")
        return


  def run(self):
    self.phase_queue = queue.Queue()
    self.phase_queue.put(PHASE.CP)

    self.global_state.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    self.global_state.sock.bind(("localhost", COORDINATOR_PORT))
    self.initialize_workers()

    st = SendThread("Coordinator", os.getpid(), self.global_state, self.phase_queue)
    rt = RecvThread(self.global_state, self.phase_queue)

    st.start()
    rt.start()

    if self._recovery_test_mode == self.RecoveryTestModes.TEST_REDUCER:
      while True:
        time.sleep(3)
        self.kill_worker(id=f"Reducer_{random.randrange(0, NUM_REDUCERS)}")

    elif self._recovery_test_mode == self.RecoveryTestModes.TEST_MAPPER:
      while True:
        time.sleep(3)
        self.kill_worker(id=f"Mapper_{random.randrange(0, NUM_MAPPERS)}")

    elif self._recovery_test_mode == self.RecoveryTestModes.TEST_BOTH:
      while True:
        time.sleep(3)
        self.kill_worker(id=f"Reducer_{random.randrange(0, NUM_REDUCERS)}")
        self.kill_worker(id=f"Mapper_{random.randrange(0, NUM_MAPPERS)}")

    elif self._recovery_test_mode == self.RecoveryTestModes.TEST_ALL:
      while True:
        time.sleep(4)
        self.kill_worker(id=f"Mapper_0")
        self.kill_worker(id=f"Reducer_0")
        self.kill_worker(id=f"Mapper_1")
        self.kill_worker(id=f"Reducer_1")

    st.join()
    rt.join()
