from typing import Final

FNAME: Final[bytes] = b"fname"
CHECKPOINT_INTERVAL : Final[float] = 0.5
HEARTBEAT_INTERVAL: Final[float] = 0.5
HEARTBEAT_TIMEOUT: Final[float] = 1
NUM_MAPPERS: Final[int] = 2
NUM_REDUCERS: Final[int] = 2
STREAMS: Final[list[bytes]] = [f"stream_{i}".encode() for i in range(NUM_MAPPERS)]

COORDINATOR_PORT: Final[int] = 12900
MAPPER_PORTS: Final[list[int]] = [COORDINATOR_PORT + i + 1 for i in range(NUM_MAPPERS)]
REDUCER_PORTS: Final[list[int]] = [MAPPER_PORTS[-1] + i + 1 for i in range(NUM_REDUCERS)]
