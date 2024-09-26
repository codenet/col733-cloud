from __future__ import annotations

import abc
import socket
import threading
from dataclasses import dataclass
from multiprocessing import Process
from time import sleep
from typing import TYPE_CHECKING, Optional
from concurrent.futures import ThreadPoolExecutor

if TYPE_CHECKING:
  from network import ConnectionStub

from core.logger import server_logger
from core.message import JsonMessage
from core.socket_helpers import STATUS_CODE, recv_message

MAX_WORKERS = 32

@dataclass
class ServerInfo:
  name: str
  host: str
  port: int

  def __hash__(self) -> int:
    return hash(f"{self.name} {self.host}:{self.port}")

  def __str__(self) -> str:
    return f"Name={self.name},Address={self.host}:{self.port},"


class Server(Process):
  """This class represents the CRAQ Server"""

  def __init__(self, info: ServerInfo, connection_stub: ConnectionStub) -> None:
    super(Server, self).__init__()
    self._info = info
    self._connection_stub = connection_stub

  def handle_client(self, client_sock: socket.socket, addr: socket.AddressInfo):
    _logger = server_logger.bind(server_name=self._info.name)
    try:
      while True:
        _logger.debug(f"Connected with {addr}")
        err_code, request = recv_message(client_sock)

        if request is None:
          _logger.critical(f"{STATUS_CODE[err_code]}")
          sr = JsonMessage(msg={"error_msg": STATUS_CODE[err_code], "error_code": err_code})
        else:
          _logger.debug(f"Received message from {addr}: {request}")
          sr = self._process_req(request)
        if sr is not None:
          _logger.debug(f"Sending message to {addr}: {sr}")
          client_sock.sendall(sr.serialize())
    except Exception as e:
      _logger.exception(e)
    finally:
      _logger.debug(f"Something went wrong! Closing the socket")
      client_sock.close()

  def run(self) -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((self._info.host, self._info.port))
    sock.listen()

    sleep(1)    # Let all servers start listening
    self._connection_stub.initalize_connections()

    _logger = server_logger.bind(server_name=self._info.name)

    _logger.info(f"Listening on {self._info.host}:{self._info.port}")

    client_handlers: list[threading.Thread] = []
    try:
      while True:
        client_sock, addr = sock.accept()
        client_handler = threading.Thread(target=self.handle_client,
                                          args=(client_sock, addr), name=f"listen#{addr[1]}")
        client_handler.daemon = True
        client_handler.start()
        client_handlers.append(client_handler)
    finally:
      sock.close()
      for client_handler in client_handlers:
        client_handler.join()

  @abc.abstractmethod
  def _process_req(self, msg: JsonMessage) -> Optional[JsonMessage]:
    raise NotImplementedError

  def __str__(self) -> str:
    return str(self._info)
