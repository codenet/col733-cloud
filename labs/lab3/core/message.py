from __future__ import annotations
import json
from typing import Final, Any, Optional


class JsonMessage:
    def __init__(self, msg: dict) -> None:
        self._msg_d: Final[dict] = msg

    @staticmethod
    def deserialize(msg: bytes) -> JsonMessage:
        msg_str = msg.decode("utf-8")
        msg_json: dict = json.loads(msg_str)
        return JsonMessage(msg=msg_json)

    @property
    def msg_bytes(self):
        return str(self).encode("utf-8")

    @property
    def msg_len(self):
        return len(self.msg_bytes)

    def serialize(self) -> bytes:
        """
        -------------------------------------------------------------
        | message-length (8-bytes) | message (message-length bytes) |
        -------------------------------------------------------------
        length:- is unsigned is integer.
        message:- is utf-8 encoded
        """
        return self.msg_len.to_bytes(8, "big") + self.msg_bytes

    def __str__(self) -> str:
        return json.dumps(self._msg_d)

    def __getitem__(self, key: str) -> Any:
        return self._msg_d[key]

    def __setitem__(self, key: str, val: Any) -> None:
        self._msg_d[key] = val

    def __contains__(self, key: str) -> bool:
        return key in self._msg_d 
        

    def get(self, key: str) -> Optional[Any]:
        return self._msg_d.get(key)
