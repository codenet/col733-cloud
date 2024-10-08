import socket
from typing import Optional, Final

from core.logger import network_logger, client_logger
from core.server import ServerInfo
from core.message import JsonMessage
from core.socket_helpers import STATUS_CODE, recv_message


class SimulatedConnectionError(Exception):
    pass


class TcpClient:
    def __init__(self, info: ServerInfo, blocking: bool = True) -> None:
        self._info = info
        self._logger = client_logger
        self._blocking: Final[bool] = blocking

    def send(self, message: JsonMessage) -> Optional[JsonMessage]:
        """
        Send message to the server and wait for response, then return the response.
        """
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        response = None

        try:
            client_socket.connect((self._info.host, self._info.port))
            self._logger.debug(
                f"Connected to server at {self._info.host}:{self._info.port}"
            )

            client_socket.sendall(message.serialize())
            self._logger.debug(
                f"Message sent to server at {self._info.host}:{self._info.port} -> {message}"
            )

            if self._blocking:
                err_code, response = recv_message(client_socket)

                if response is None:
                    self._logger.critical(f"{STATUS_CODE[err_code]}")
                    return None
        except Exception as e:
            self._logger.exception(e)
        finally:
            client_socket.close()
            self._logger.debug(
                f"Connection with server at {self._info.host}:{self._info.port} closed."
            )

        return response


class ConnectionStub:
    def __init__(self, connections: set[ServerInfo]) -> None:
        self._connections: dict[str, ServerInfo] = {}
        for si in connections:
            self._connections[si.name] = si

        self._blocking_clients: dict[str, TcpClient] = {}
        self._dc_servers: set[str] = set()

    def initalize_connections(self) -> None:
        for connection in self._connections.values():
            self._blocking_clients[connection.name] = TcpClient(connection)

    # def get_connection(self, to: str) -> Optional[TcpClient]:
    #     if to in self._dc_servers:
    #         return None
    #     return self._blocking_clients[to]

    def send(self, from_: str, to: str, message: JsonMessage) -> Optional[JsonMessage]:
        network_logger.debug(f"Sending Message from {from_} to {to}: {message}")

        assert (
            to in self._blocking_clients
        ), f"Connection {to} doesn't exist in {from_} {self._blocking_clients}"
        channel = self._blocking_clients[to]

        if to in self._dc_servers:
            raise SimulatedConnectionError()

        return channel.send(message)

    def sever_connection(self, peer_name: str) -> None:
        assert peer_name in self._connections, "Tried to sever non-existing connection"
        self._dc_servers.add(peer_name)

    def unsever_connection(self, peer_name: str) -> None:
        assert peer_name in self._connections, "Tried to unsever non-existing connection"
        self._dc_servers.remove(peer_name)

    def all_peer_names(self) -> set[str]:
        return set(self._connections.keys())

    def connected_peer_names(self) -> set[str]:
        return self.all_peer_names() - set(self._dc_servers)
