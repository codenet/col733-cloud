import sys
from logging import INFO, DEBUG, WARNING

from loguru import logger
logger.remove()

_server_fmt = "<green>{time:HH:mm:ss}</green> <blue>{level}</blue> <cyan>{thread.name} {extra[server_name]}</cyan> {message}"
logger.add(
  # "logs/server.log",
  sys.stdout,
  filter=lambda record: record["extra"].get("name") == "s",
  format=_server_fmt,
  level=INFO)

_client_fmt = "<green>{time:HH:mm:ss}</green> <blue>{level}</blue> <cyan>{extra[server_name]}</cyan> {message}"
logger.add(sys.stdout,
    # "logs/client.log",
           format=_client_fmt,
           filter=lambda record: record["extra"].get("name") == "c",
           # level=INFO)
           level=WARNING)

_network_fmt = "<green>{time:HH:mm:ss}</green> <blue>{level}</blue> {message}"
logger.add(sys.stdout,
           # "logs/network.log",
           filter=lambda record: record["extra"].get("name") == "n",
           format=_network_fmt,
           level=INFO)

server_logger = logger.bind(name="s")
client_logger = logger.bind(name="c")
network_logger = logger.bind(name="n")

def set_client_logfile(file: str) -> int:
  sink_id = logger.add(file, format=_client_fmt, filter=lambda record: record["extra"].get("name") == "c", level=INFO)
  return sink_id

def remove_client_logfile(sink_id: int) -> None:
  logger.remove(sink_id)
