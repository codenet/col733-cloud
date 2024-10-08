from __future__ import annotations

import time
from typing import cast, Any, Optional

from bayou.client import BayouClient
from bayou.ctrlmsg import RequestTypes, BayouResponse
from bayou.server import BayouServer
from bayou.storage import State, LogEntry, LogicalTime
from core.message import JsonMessage
from core.network import ConnectionStub
from core.server import ServerInfo


class AppState(State):
    def __init__(self) -> None:
        self.s = ""

    def __repr__(self) -> str:
        return self.s

    def __eq__(self, other: object) -> bool:
        if isinstance(other, AppState):
            return self.s == other.s
        raise ValueError


class AppLogEntry(LogEntry):
    def __init__(self, char: str, ltime: LogicalTime) -> None:
        super().__init__(msg=JsonMessage({"ltime": [ltime.ts, ltime.name]}))
        self.char = char

    def __repr__(self) -> str:
        return f"{self.ltime}; {self.char}"

    def do(self, state: State) -> None:
        tstate = cast(AppState, state)
        # TODO 1:- Apply this logEntry on the state 
        raise NotImplemented

    def undo(self, state: State) -> None:
        tstate = cast(AppState, state)
        # TODO 2:- Apply this logEntry on the state 
        raise NotImplemented

    def to_dict(self) -> dict[str, Any]:
        return {
            "char": self.char,
            "ltime": self.ltime.serialize(),
            "req_type": RequestTypes.APPEND_CHAR.name,
        }


class BayouAppServer(BayouServer):
    def __init__(
        self,
        info: ServerInfo,
        connection_stub: ConnectionStub,
        is_master: bool,
        peers: list[ServerInfo],
    ) -> None:
        super().__init__(info, connection_stub, is_master, peers, AppState())

    def deserialize(self, msg: JsonMessage, req_type: str) -> LogEntry:
        match req_type:
            case RequestTypes.APPEND_CHAR.name:
                if "ltime" in msg:
                    ltime = LogicalTime(msg["ltime"][0], msg["ltime"][1])
                else:
                    ltime = LogicalTime(self.name, time.monotonic_ns())
                return AppLogEntry(ltime=ltime, char=msg["char"])
            case _:
                raise AssertionError("Invalid Request")

    def states(self) -> tuple[str, str]:
        a_committed_st = cast(AppState, self.storage.committed_st)
        a_tentative_st = cast(AppState, self.storage.tentative_st)
        return a_committed_st.s, a_tentative_st.s

    def respond(self, msg: JsonMessage, req_type: str) -> Optional[JsonMessage]:
        if req_type != RequestTypes.GET_STRING.name:
            return None
        c, t = self.states()
        return JsonMessage({"status": "OK", "committed": c, "tentative": t})


class BayouAppClient(BayouClient):
    def append_char(self, char: str) -> JsonMessage:
        assert len(char) == 1
        return self._send(
            JsonMessage(msg={"type": RequestTypes.APPEND_CHAR.name, "char": char})
        )

    def get_string(self) -> JsonMessage:
        return self._send(JsonMessage(msg={"type": RequestTypes.GET_STRING.name}))
