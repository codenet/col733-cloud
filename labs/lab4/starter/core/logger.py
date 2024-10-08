from loguru import logger

_server_fmt = "{time} {level} {extra[server_name]} {message}"
logger.add(
    "logs/server.log",
    filter=lambda record: record["extra"].get("name") == "s",
    format=_server_fmt,
)

logger.add("logs/client.log", filter=lambda record: record["extra"].get("name") == "c")

_network_fmt = "{time} {level} {message}"
logger.add(
    "logs/network.log",
    filter=lambda record: record["extra"].get("name") == "n",
    format=_network_fmt,
)

server_logger = logger.bind(name="s")
client_logger = logger.bind(name="c")
network_logger = logger.bind(name="n")
