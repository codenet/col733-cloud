import threading
import time
from abc import abstractmethod
from typing import Optional

from sortedcontainers import SortedList  # type: ignore

from bayou.ctrlmsg import AntiEntropyReq, RequestTypes, SeverConnRequest, UnSeverConnRequest
from bayou.storage import LogEntry, Storage, State
from core.message import JsonMessage
from core.network import ConnectionStub, SimulatedConnectionError
from core.server import Server, ServerInfo

ok = JsonMessage({"status": "OK"})

class BayouServer(Server):
  """This class represents the Bayou Server"""

  def __init__(self, info: ServerInfo, connection_stub: ConnectionStub, is_master: bool, peers: list[ServerInfo],
               state: State) -> None:
    super().__init__(info, connection_stub)
    self._info = info
    self._is_master = is_master
    self._state = state
    self._peers = peers
    self._storage: Optional[Storage] = None

  @property
  def storage(self) -> Storage:
    if self._storage is None:
      self._storage = Storage([p.name for p in self._peers], self._state)
    return self._storage

  def pre_run(self) -> None:
    threading.Thread(target=self._anti_entropy, args=()).start()

  def _process_req(self, msg: JsonMessage) -> JsonMessage:
    req_type = msg.pop("type")
    try:
      match req_type:
        case None:
          return JsonMessage({"status": "Err", "error": "Must specify type of request"})
        case RequestTypes.SEVER_CONN.name:
          self._connection_stub.sever_connection(
            SeverConnRequest(msg).peer_name
          )
          return ok
        case RequestTypes.UNSEVER_CONN.name:
          self._connection_stub.unsever_connection(UnSeverConnRequest(msg).peer_name)
          return ok
        case RequestTypes.ANTI_ENTROPY.name:
          req = AntiEntropyReq.from_msg(msg)
          committed, tentative = self.storage.anti_entropy(req.c, req.f)
          return JsonMessage({
            "committed": [e.to_dict() for e in committed],
            "tentative": [e.to_dict() for e in tentative],
          })
        case _:
          return self._process_app_req(msg, req_type)
    except AssertionError as e:
      return JsonMessage({"status": "Err", "error": str(e)})

  def _process_app_req(self, msg: JsonMessage, req_type: str) -> JsonMessage:
    response = self.respond(msg, req_type)
    if response is not None:
      return response

    log_entry = self.deserialize(msg, req_type)
    assert log_entry is not None
    if self._is_master:
      self.storage.commit([log_entry])
      state = "COMMITTED"
    else:
      self.storage.tentative(SortedList([log_entry]))
      state = "TENTATIVE"
    return JsonMessage({"status": "OK", "write_state": state})

  def __send_anti_entropy(self, peer: str) -> tuple[list[LogEntry], SortedList[LogEntry]]:
    response = self._connection_stub.send(self.name, peer, AntiEntropyReq(self.storage.c, self.storage.f).to_msg())
    assert response is not None
    committed, tentative = response["committed"], response["tentative"]

    committed_logs = [self.deserialize(c, c["req_type"]) for c in committed]
    tentative_logs = SortedList([self.deserialize(t, t["req_type"]) for t in tentative], key=lambda l: l.ltime)

    if self._is_master:
      # TODO-5: Do something special
      raise NotImplemented()

    return committed_logs, tentative_logs


  def _anti_entropy(self) -> None:
    """
    Performs anti-entropy with one other server that it can communicate to.
    """
    time.sleep(2)
    while True:
      for peer in self._peers:
        if peer.name != self.name:
          try:
            committed, tentative = self.__send_anti_entropy(peer.name)
            self.storage.apply(committed, tentative)
            self.logger.debug(
              f"{self.name} Applied log from {peer.name}, {self.storage.committed_st}, {self.storage.tentative_st}, {committed}, {tentative}")
          except SimulatedConnectionError:
            self.logger.warning(f"No Connection with {peer.name}")
          time.sleep(0.1)

  @abstractmethod
  def deserialize(self, msg: JsonMessage, req_type: str) -> LogEntry:
    raise NotImplementedError

  @abstractmethod
  def respond(self, msg: JsonMessage, req_type: str) -> Optional[JsonMessage]:
    raise NotImplementedError
