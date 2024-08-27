import struct
import json
import enum
from functools import lru_cache

class MT(enum.IntEnum):
    HEARTBEAT = 0                # mapper -> coordinator, reducer -> coordinator
    CHECKPOINT = 1               # coordinator -> mapper
    FWD_CHECKPOINT = 2           # mapper -> reducer
    WORD_COUNT = 3               # mapper -> reducer
    CHECKPOINT_ACK = 4           # mapper -> coordinator, reducer -> coordinator
    EXIT = 5                     # coordinator -> mapper, coordinator -> reducer
    DONE = 6                     # mapper -> coordinator
    LAST_CHECKPOINT_ACK = 7      # mapper -> coordinator, reducer -> coordinator
    RECOVER = 8                  # coordinator -> mapper , coordinator -> reducer
    RECOVERY_ACK = 9             # mapper -> coordinator, reducer -> coordinator

    @classmethod
    @lru_cache()
    def num_messages(cls) -> int:
        return len(list(map(lambda c: c.value, cls)))


class Message:
    # Message has following attributes: (type, src, kwargs)
    BUFFER_SIZE = 1024

    def __init__(self, msg_type: MT, source: str, **kwargs):
        if msg_type >= MT.num_messages():
            raise ValueError(f"Unknown message type: {msg_type}")
        self.msg_type = msg_type
        self.source = source
        self.kwargs = kwargs

    def serialize(self) -> bytes:
        # Convert message to a dictionary
        message_dict = {
            "type": self.msg_type,
            "source": self.source,
        }
        for k,v in self.kwargs.items():
            message_dict[k] = v

        message_json = json.dumps(message_dict)
        message_bytes = message_json.encode('utf-8')
        message_length = len(message_bytes)
        full_message = struct.pack('!I', message_length) + message_bytes
        padded_message = full_message.ljust(self.BUFFER_SIZE, b'\x00')
        return padded_message

    @staticmethod
    def deserialize(message_bytes: bytes) -> 'Message':
        message_length = struct.unpack('!I', message_bytes[:4])[0]
        message_json = message_bytes[4:4 + message_length].decode('utf-8')
        message_dict = json.loads(message_json)
        msg_type = MT(message_dict["type"])
        source = message_dict["source"]
        kwargs = {k: v for k, v in message_dict.items() if k not in {"type", "source"}}

        return Message(msg_type, source, **kwargs)
