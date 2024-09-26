import socket
from typing import Optional, Final

from core.logger import network_logger
from core.server import ServerInfo
from core.message import JsonMessage
from core.socket_helpers import STATUS_CODE, recv_message


class TcpClient:
  def __init__(self, info: ServerInfo, blocking: bool = True, sock_pool_sz: int = 1) -> None:
    self._info = info
    self._logger = network_logger
    self._blocking: Final[bool] = blocking
    self._client_sockets: Optional[list[socket.socket]] = None
    self._sock_pool_sz: Final[int] = sock_pool_sz

  @property
  def client_sockets(self) -> list[socket.socket]:
    if self._client_sockets is None:
      self._client_sockets = []
      for i in range(self._sock_pool_sz):
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((self._info.host, self._info.port))
        self._client_sockets.append(client_socket)
        self._logger.debug(f"Created connection pool of size {self._sock_pool_sz} with server "
                       f"at {self._info.host}:{self._info.port}")

    return self._client_sockets

  def get_sock(self) -> socket.socket:
    assert len(self.client_sockets) > 0, "Exhausted sockets"
    return self.client_sockets.pop()

  def release_sock(self, sock: socket.socket):
    return self.client_sockets.append(sock)
  
  def _close_client_sockets(self):
    if self._client_sockets is not None:
      for client_socket in self._client_sockets:
        try:
          client_socket.close()
          self._logger.debug(f"Connection with server at {self._info.host}:{self._info.port} closed.")
        except Exception as e:
          self._logger.exception(e)
      self._client_sockets = None

  def send(self, message: JsonMessage) -> JsonMessage:
    """
    Send message to the server and wait for response, then return the response.
    """
    response = None
    client_socket = self.get_sock()

    try:

      client_socket.sendall(message.serialize())
      self._logger.debug(f"Message sent to server at {self._info.host}:{self._info.port} -> {message}")

      if self._blocking:
        err_code, response = recv_message(client_socket)

        if response is None:
          self._logger.critical(f"{STATUS_CODE[err_code]}")
          return JsonMessage({"status": STATUS_CODE[err_code]})
    except Exception as e:
      self._logger.exception(e)
    finally:
      self.release_sock(client_socket)

    return response

  def __del__(self):
    self._close_client_sockets()


class ConnectionStub:
  def __init__(self, connections: set[ServerInfo], sock_pool_sz: int) -> None:
    self._connections: dict[str, ServerInfo] = {}
    for si in connections:
      self._connections[si.name] = si
    self._blocking_clients: dict[str, TcpClient] = {}
    self._non_blocking_clients: dict[str, TcpClient] = {}
    self._sock_pool_sz: Final[int] = sock_pool_sz

  def initalize_connections(self):
    for connection in self._connections.values():
      self._blocking_clients[connection.name] = TcpClient(connection, sock_pool_sz=self._sock_pool_sz)
      self._non_blocking_clients[connection.name] = TcpClient(connection, blocking=False, sock_pool_sz=self._sock_pool_sz)

  def get_connection(self, to: str, blocking: bool = True) -> TcpClient:
    if blocking:
      return self._blocking_clients[to]
    return self._non_blocking_clients[to]

  def send(self, from_: str, to: str, message: JsonMessage, blocking: bool = True) -> JsonMessage:
    network_logger.debug(f"Sending Message from {from_} to {to}: {message}")

    channel: TcpClient
    if not blocking:
      assert to in self._non_blocking_clients, f"Connection {to} doesn't exist in {from_} {self._non_blocking_clients}"
      channel = self._non_blocking_clients[to]
    else:
      assert to in self._blocking_clients, f"Connection {to} doesn't exist in {from_} {self._blocking_clients}"
      channel = self._blocking_clients[to]

    return channel.send(message)

  def broadcast(self, message: JsonMessage) -> None:
    network_logger.debug("Broadcasting!")
    for name, client in self._non_blocking_clients.items():
      network_logger.debug(f"Sending Message to {name}: {message}")
      client.send(message)
