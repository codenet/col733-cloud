import datetime
from abc import ABC, abstractmethod
from enum import Enum, IntEnum
from multiprocessing import Process
import os
import signal
import socket
from typing import Final, Optional
import time
import threading
import logging
import queue

from mapper import Mapper
from constants import HEARTBEAT_INTERVAL, HEARTBEAT_TIMEOUT, CHECKPOINT_INTERVAL, NUM_MAPPERS, NUM_REDUCERS, STREAMS, \
  MAPPER_PORTS, REDUCER_PORTS, COORDINATOR_PORT
from reducer import Reducer
from message import Message, MT

from mylog import Logger
logging = Logger().get_logger()

class WorkerState:
  def __init__(self, idx: int, is_mapper: bool, addr: tuple[str, int]):
    self.idx: Final[int] = idx
    self.id: Final[str] = f"{'Mapper' if is_mapper else 'Reducer'}_{idx}"
    self.is_mapper: Final[bool] = is_mapper
    self.addr: Final[tuple[str, int]] = addr  # for udp connection ("localhost", port)

    self.last_hb_recvd: int = 0  # when did we receive last heartbeat (in seconds)
    self.last_cp_id: int = 0  # (0 initially) the id of last checkpoint a worker made
    self.recovery_id: int = 0
    self.is_done: bool = False  # only for mappers (have mappers finished reading their stream)
    self.last_checkpoint_done: bool = False # has a worker finished done its last checkpoint
    self.process: Process

  def reset(self):
    self.is_done = False
    self.last_checkpoint_done = False

  def start_worker(self, restart: bool = False) -> None:
    # restart flag: when we are trying to restart a worker. killing the process first.
    if restart:
      assert self.process is not None
      self.process.kill()

    if self.is_mapper:
      self.process = Mapper(self.idx, REDUCER_PORTS, MAPPER_PORTS[self.idx])
    else:
      self.process = Reducer(self.idx, REDUCER_PORTS[self.idx], NUM_MAPPERS)
    self.process.start()

class PHASE(IntEnum):
  CP = 1
  RECOVER_REDUCER = 2
  RECOVER_MAPPER = 3
  LAST_CP = 4
  EXITING = 5

class CoordinatorState():
  def __init__(self) -> None:
    self.phase: PHASE = PHASE.CP
    self.next_recovery_id: int = 0
    self.next_cp_id: int = 1
    self.workers: dict[str, WorkerState] = {}
    self.sock: Optional[socket.socket] = None
  
  # function to calculate min(last_checkpoint_id) for all workers
  # during recovery, all workers should recover from this checkpoint!
  def last_completed_checkpoint_id(self):
    checkpoint_id = 1_000_000  # random large number
    for _, ws in self.workers.items():
      if checkpoint_id > ws.last_cp_id:
        checkpoint_id = ws.last_cp_id
    if checkpoint_id == 0: # this means there exist some worker has not checkpointed yet
      checkpoint_id = -1 # for this, we use -1 as id, which means recover from beginning 
      # for workers, you would need to handle this appropriately when they receive a recover message with
      # last checkpoint id as -1. (HINT: Recover from beginning state)
    return checkpoint_id

class RcvMsg(ABC):
  @abstractmethod
  def update(self, state: CoordinatorState, source: str) -> Optional[PHASE]:
    """
      Do not implement this, this is an abstract method. Implement this in child classes.
      Input: state -> Current Coordinator state,
             source -> id of the worker from where this message was received from.
      Output: phase -> New phase to transition to after receiving the message.

      Semantics of the function is as follows:-
        1. Change the coordinator state (if required).
        2. Return the new PHASE if PHASE transition is necessary.
    """
    raise NotImplementedError

class HBRecvMsg(RcvMsg):
  def update(self, state: CoordinatorState, source: str) -> Optional[PHASE]:
    logging.debug(f"Coordinator received heartbeat from {source}")
    state.workers[source].last_hb_recvd = int(time.time())
    return None

class CkptAckRecvMsg(RcvMsg):
  def __init__(self, checkpoint_id: str):
    self.checkpoint_id: Final[int] = int(checkpoint_id)

  def update(self, state: CoordinatorState, source: str) -> Optional[PHASE]:
    pass
    # TODO: Take appropriate action when coordinator receives checkpoint_ack message from a worker


class LastCkptAckRecvMsg(RcvMsg):
  def __init__(self, checkpoint_id: str):
    assert int(checkpoint_id) == 0

  def update(self, state: CoordinatorState, source: str) -> Optional[PHASE]:
    pass
    # TODO: Take appropriate action when coordinator receives last_checkpoint_ack message from a worker

class RecoveryAckRecvMsg(RcvMsg):
  def __init__(self, recovery_id: int):
    self.recovery_id = recovery_id

  def update(self, state: CoordinatorState, source: str) -> Optional[PHASE]:
    pass
    # TODO: Take appropriate action when coordinator receives recovery_ack message from worker

class DoneRecvMsg(RcvMsg):
  def update(self, state: CoordinatorState, source: str) -> Optional[PHASE]:
    logging.info(f"Received DONE message from {source}")
    assert state.workers[source].is_mapper == True, "Only mappers should send DONE message"
    state.workers[source].is_done = True
    are_all_mappers_done = True
    for _, ws in state.workers.items():
      if ws.is_mapper:
        if ws.is_done == False:
          are_all_mappers_done = False

    if are_all_mappers_done:
      return PHASE.EXITING
      # TODO: Move to LAST_CP instead
    return None

# converting received message, into appropriate message type
def msg_factory(message: Message) -> RcvMsg:
  if message.msg_type == MT.HEARTBEAT:
    return HBRecvMsg()
  elif message.msg_type == MT.CHECKPOINT_ACK:
    return CkptAckRecvMsg(message.kwargs["checkpoint_id"])
  elif message.msg_type == MT.DONE:
    return DoneRecvMsg()
  elif message.msg_type == MT.LAST_CHECKPOINT_ACK:
    return LastCkptAckRecvMsg(message.kwargs["checkpoint_id"])
  elif message.msg_type == MT.RECOVERY_ACK:
    return RecoveryAckRecvMsg(message.kwargs["recovery_id"])
  else:
    logging.error(f"Unknown message type {message.msg_type}! Bad situtation.")
    raise Exception(f"Unknown message type {message.msg_type}! Bad situtation.")
    

class RecvThread(threading.Thread):
  def __init__(self, state: CoordinatorState, phase_queue: queue.Queue[PHASE]):
    super().__init__()
    self.state = state
    self.phase_queue = phase_queue
    signal.signal(signal.SIGALRM, self.monitor_health)
    signal.setitimer(signal.ITIMER_REAL, HEARTBEAT_INTERVAL, HEARTBEAT_INTERVAL)

  # monitoring health of all the workers. This handler will be invoked every HEARTBEAT_INTERVAL seconds.
  # Here we are checking that for all workers, (current_time - last_heartbeat_time <= HEARTBEAT_TIMEOUT)
  # If this is not the case, this means that the worker is down: We need to take appropriate actions.
  def monitor_health(self, signum, frame):
    logging.info("-- monitoring heartbeats --")
    recover = False
    for _, ws in self.state.workers.items():
      last = ws.last_hb_recvd
      cur = int(time.time())
      diff = cur - last
      logging.debug(f"{_} sent last heartbeat {diff} seconds ago")
      if diff > HEARTBEAT_TIMEOUT:
        logging.critical(f"{_} is facing heartbeat timeouts")
        ws.start_worker(restart=True)
        recover = True
      
    if recover:
      time.sleep(0.2)
      # TODO: Take appropriate actions (the worker is down)

  def run(self):
    logging.info("RECV thread of coordinator started!")
    while True:
      response, _ = self.state.sock.recvfrom(1024)
      message = Message.deserialize(response)  # type = Message(msg_type, source, **kwargs)
      logging.debug(f"Received message of type '{message.msg_type.name}' from '{message.source}'")
      msg = msg_factory(message)
      new_phase = msg.update(self.state, message.source)  # it will return new phase, in case there is some phase change
      if new_phase is not None: # adding new phase into queue, so that send thread can read and take appropriate actions
        logging.info(f"Moving from {self.state.phase.name} to {new_phase.name}")
        self.state.phase = new_phase
        self.phase_queue.put(new_phase)

class SendMsg(ABC):
  def send(self, sock: Optional[socket.socket], addr: tuple[str, int]) -> None:
    assert sock is not None
    try:
      b_msg = self.encode()
      sock.sendto(b_msg, addr)
    except socket.error as e:
      logging.error(f"Error sending data: {e}")
    except Exception as e:
      logging.error(f"Unexpected error: {e}")

  @abstractmethod
  def encode(self) -> bytes:
    raise NotImplementedError

class CPMsg(SendMsg):
  def __init__(self, checkpoint_id: int, recovery_id: int):
    self.checkpoint_id = checkpoint_id
    self.recovery_id = recovery_id
  
  def encode(self) -> bytes:
    return Message(msg_type=MT.CHECKPOINT, source="Coordinator", checkpoint_id=self.checkpoint_id, recovery_id= self.recovery_id).serialize()


class RecoveryMsg(SendMsg):
  def __init__(self, checkpoint_id: int, recovery_id: int):
    self.checkpoint_id = checkpoint_id
    self.recovery_id = recovery_id

  def encode(self) -> bytes:
    return Message(msg_type=MT.RECOVER, source="Coordinator",
                   recovery_id= self.recovery_id, checkpoint_id=self.checkpoint_id).serialize()

class ExitMsg(SendMsg):
  def encode(self) -> bytes:
    return Message(msg_type=MT.EXIT, source="Coordinator").serialize()


class SendThread(threading.Thread):
  def __init__(self, id: str, pid: int, state: CoordinatorState, phase_queue: queue.Queue[PHASE]):
    super().__init__()
    self.id: Final[str] = id
    self.pid: Final[int] = pid
    self.state: Final[CoordinatorState] = state
    self.phase_queue: queue.Queue[PHASE] = phase_queue


  """
    *_phase methods define what to do in a certain PHASE.
  """
  def cp_phase(self):
    if self.state.phase != PHASE.CP:
      return
    
    # TODO: complete the behavior when system is in CP phase

  def recover_phase(self, is_mapper: bool) -> None:
    if is_mapper:
      assert self.state.phase == PHASE.RECOVER_MAPPER
    else:
      assert self.state.phase == PHASE.RECOVER_REDUCER

    # TODO: complete the behavior when system is in RECOVERY phase

  def last_cp_phase(self):
    assert self.state.phase == PHASE.LAST_CP

    # TODO: complete the behavior when system is in Last_CP phase

  def exit_phase(self, start_time):
    assert self.state.phase == PHASE.EXITING
    logging.info(f"{self.id} sending exit command to workers")
    for _, ws in self.state.workers.items():
      ExitMsg().send(self.state.sock, ws.addr)
    logging.critical(f"{self.id} exiting!")
    # self.state.send_socket.close()
    end_time = datetime.datetime.now()
    logging.info(f"Job Finished at {end_time}")
    logging.info(f"Total Time Taken = {end_time - start_time}")
    os.kill(self.pid, signal.SIGKILL)

  def run(self):
    start_time = datetime.datetime.now()
    logging.info(f"Starting Job at {start_time}")
    logging.info("SENDING thread of coordinator started!")
    while True:
      current_phase = None
      if not self.phase_queue.empty():
        current_phase = self.phase_queue.get()

      if current_phase is None:
        continue

      elif current_phase == PHASE.CP:
        logging.info("The current phase is Checkpointing phase")
        time.sleep(CHECKPOINT_INTERVAL)
        self.cp_phase()
      
      elif current_phase == PHASE.RECOVER_REDUCER:
        logging.info("The current phase is Reducer Recovery phase")
        self.recover_phase(is_mapper=False)

      elif current_phase == PHASE.RECOVER_MAPPER:
        logging.info("The current phase is Mapper Recovery phase")
        self.recover_phase(is_mapper=True)

      elif current_phase == PHASE.LAST_CP:
        logging.info("The current phase is Last Checkpoint phase")
        self.last_cp_phase()

      elif current_phase == PHASE.EXITING:
        logging.info("The current phase is Exiting phase")
        self.exit_phase(start_time)

      else:
        logging.error("Unknown global phase. Exiting!")
        break

