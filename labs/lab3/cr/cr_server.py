import json
from enum import Enum
from typing import Optional, Final

from core.logger import server_logger
from core.message import JsonMessage, JsonMessage
from core.network import ConnectionStub
from core.server import Server, ServerInfo


class RequestType(Enum):
  SET = 1
  GET = 2


class KVGetRequest:
  def __init__(self, msg: JsonMessage):
    self._json_message = msg
    assert "key" in self._json_message, self._json_message

  @property
  def key(self) -> str:
    return self._json_message["key"]

  @property
  def json_msg(self) -> JsonMessage:
    return self._json_message


class KVSetRequest:
  def __init__(self, msg: JsonMessage):
    self._json_message = msg
    assert "key" in self._json_message, self._json_message
    assert "val" in self._json_message, self._json_message

  @property
  def key(self) -> str:
    return self._json_message["key"]

  @property
  def val(self) -> str:
    return self._json_message["val"]

  @property
  def version(self) -> Optional[int]:
    return self._json_message.get("ver")

  @version.setter
  def version(self, ver: int) -> None:
    self._json_message['ver'] = ver

  @property
  def json_msg(self) -> JsonMessage:
    return self._json_message

  def __str__(self) -> str:
    return str(self._json_message)


class CRServer(Server):
  """Chain replication. GET is only served by tail"""

  def __init__(self, info: ServerInfo, connection_stub: ConnectionStub,
               next: Optional[ServerInfo], prev: Optional[ServerInfo],
               tail: ServerInfo) -> None:
    super().__init__(info, connection_stub)
    self.next: Final[Optional[str]] = None if next is None else next.name
    self.prev: Final[Optional[str]] = prev if prev is None else prev.name
    self.tail: Final[str] = tail.name
    self.d: dict[str, str] = {} # Key-Value store

  def _process_req(self, msg: JsonMessage) -> JsonMessage:
    if msg.get("type") == RequestType.GET.name:
      return self._get(KVGetRequest(msg))
    elif msg.get("type") == RequestType.SET.name:
      return self._set(KVSetRequest(msg))
    else:
      server_logger.critical("Invalid message type")
      return JsonMessage({"status": "Unexpected type"})

  def _get(self, req: KVGetRequest) -> JsonMessage:
    assert self.next is None, f"GET shall only be sent to the TAIL! I am {self.name}"
    _logger = server_logger.bind(server_name=self._info.name)
    val = self.d[req.key]
    _logger.debug(f"Getting {req.key} as {val}")
    return JsonMessage({"status": "OK", "val": val})

  def _set(self, req: KVSetRequest) -> JsonMessage:
    _logger = server_logger.bind(server_name=self._info.name)
    _logger.debug(f"Setting {req.key} to {req.val}")
    self.d[req.key] = req.val
    if self.next is not None:
      # Send blocking request
      return self._connection_stub.send(from_=self._info.name, to=self.next,
                                        message=req.json_msg)
    else:
      return JsonMessage({"status": "OK"})

