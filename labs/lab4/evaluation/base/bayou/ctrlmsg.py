from __future__ import annotations

from enum import Enum
from typing import Any

from bayou.storage import VectorTime, LogicalTime
from core.message import JsonMessage


class WriteState(Enum):
  TENTATIVE = 0
  COMMITTED = 1
  REJECTED = 2


class RequestTypes(Enum):
  SEVER_CONN = 0
  UNSEVER_CONN = 1
  ANTI_ENTROPY = 2

  # Application requests
  APPEND_CHAR = 3
  GET_STRING = 4


class SeverConnRequest:
  def __init__(self, msg: JsonMessage) -> None:
    assert "peer_name" in msg, "peer_name is required in SeverConnRequest."
    self._msg = msg

  @property
  def peer_name(self) -> str:
    return str(self._msg["peer_name"])


class UnSeverConnRequest:
  def __init__(self, msg: JsonMessage) -> None:
    assert "peer_name" in msg, "peer_name is required in UnSeverConnRequest."
    self._msg = msg

  @property
  def peer_name(self) -> str:
    return str(self._msg["peer_name"])


class AntiEntropyReq:
  def __init__(self, c: VectorTime, f: VectorTime) -> None:
    self._c_vector = c
    self._f_vector = f

  @property
  def c(self) -> VectorTime:
    return self._c_vector

  @property
  def f(self) -> VectorTime:
    return self._f_vector

  @staticmethod
  def from_msg(msg: JsonMessage) -> "AntiEntropyReq":
    assert "c" in msg, "c must be in the anti-entropy req"
    assert "f" in msg, "f must be in the anti-entropy req"

    assert isinstance(msg["c"], dict)
    assert isinstance(msg["f"], dict)

    c_vector = []
    for n, t in msg["c"].items():
      assert isinstance(n, str)
      assert isinstance(t, int)
      c_vector.append(LogicalTime(n, t))

    f_vector = []
    for n, t in msg["f"].items():
      assert isinstance(n, str)
      assert isinstance(t, int)
      f_vector.append(LogicalTime(n, t))

    return AntiEntropyReq(VectorTime(c_vector), VectorTime(f_vector))

  def to_msg(self) -> JsonMessage:
    return JsonMessage(
      msg={
        "type": RequestTypes.ANTI_ENTROPY.name,
        "c": self.c.to_dict(),
        "f": self.f.to_dict(),
      })


class BayouResponse:
  def __init__(
          self, status: bool, write_state: WriteState, payload: dict[str, Any]
  ) -> None:
    self._status = status
    self._write_state: WriteState = write_state
    self._payload = payload

  def to_json_message(self) -> JsonMessage:
    return JsonMessage(
      msg={
        "status": "OK" if self._status else "Err",
        "write_state": self._write_state.name,
        "payload": self._payload,
      }
    )

  @staticmethod
  def from_json_message(json_msg: JsonMessage) -> BayouResponse:
    assert "status" in json_msg, "Status must be in msg"
    assert json_msg["status"] in {"OK", "Err"}, "Status must be {OK, Err}"
    assert "payload" in json_msg, "Payload must be present"
    assert isinstance(json_msg["payload"], dict), "Payload must be dict"
    assert "write_state" in json_msg, "write state must be in msg"
    assert json_msg["write_state"] in [e.name for e in
                                       WriteState], f"write state must be {[e.name for e in WriteState]}"

    return BayouResponse(json_msg["status"], WriteState[json_msg["write_state"]], json_msg["payload"])

  @property
  def status(self) -> bool:
    return str(self._status) == "OK"

  @property
  def write_state(self) -> WriteState:
    return self._write_state

  @property
  def payload(self) -> dict[str, Any]:
    return self._payload

  def __getattr__(self, name: str) -> Any:
    try:
      return self._payload[name]
    except KeyError:
      raise AttributeError()
