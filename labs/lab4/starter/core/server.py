from __future__ import annotations

import abc
import socket
import threading
from dataclasses import dataclass
from multiprocessing import Process
from time import sleep
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
  from core.network import ConnectionStub

from core.logger import server_logger
from core.message import JsonMessage
from core.socket_helpers import STATUS_CODE, recv_message


@dataclass
class ServerInfo:
  name: str
  port: int
  host: str = "localhost"

  def __hash__(self) -> int:
    return hash(f"{self.name} {self.host}:{self.port}")

  def __str__(self) -> str:
    return f"Name={self.name},Address={self.host}:{self.port},"


class Server(Process):
  """This class represents the Bayou Server"""

  def __init__(self, info: ServerInfo, connection_stub: ConnectionStub) -> None:
    super(Server, self).__init__(name=info.name)
    self._info = info
    self._connection_stub = connection_stub
    self._logger = None

  def handle_client(self, client_sock: socket.socket, addr: socket.AddressInfo) -> None:
    with client_sock:
      self.logger.debug(f"Connected with {addr}")
      err_code, request = recv_message(client_sock)

      sr = None
      if request is None:
        self.logger.critical(f"{STATUS_CODE[err_code]}")
        sr = JsonMessage(msg={"error_msg": STATUS_CODE[err_code], "error_code": err_code})
      else:
        self.logger.debug(f"Received message from {addr}: {request}")
        sr = self._process_req(request)
      if sr is not None:
        self.logger.debug(f"Sending message to {addr}: {sr}")
        client_sock.sendall(sr.serialize())

  def run(self) -> None:
    self.pre_run()

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((self._info.host, self._info.port))
    sock.listen()

    sleep(1)    # Let all servers start listening
    self._connection_stub.initalize_connections()

    # TODO: Handle Exceptions

    self.logger.info(f"Listening on {self._info.host}:{self._info.port}")

    client_handlers: list[threading.Thread] = []
    try:
      while True:
        client_sock, addr = sock.accept()
        client_handler = threading.Thread(target=self.handle_client, args=(client_sock, addr))
        client_handler.start()
        client_handlers.append(client_handler)
    finally:
      sock.close()
      for client_handler in client_handlers:
        client_handler.join()

  @abc.abstractmethod
  def _process_req(self, req: JsonMessage) -> Optional[JsonMessage]:
    raise NotImplementedError

  def __str__(self) -> str:
    return str(self._info)

  def pre_run(self) -> None:
    pass

  @property
  def logger(self):
    if self._logger is None:
      self._logger = server_logger.bind(server_name=self._info.name)
    return self._logger
    
