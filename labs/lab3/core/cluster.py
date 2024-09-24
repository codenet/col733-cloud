from time import sleep

from core.logger import server_logger
from core.network import ConnectionStub
from core.server import Server, ServerInfo


class ClusterManager:
  """
  This class manages a cluster of Craq servers. It is responsible for starting
  servers and establishing connections between them according to a specified topology.

  Attributes:
      _server_names (set[str]): A set of server names.
      _master (str): The name of the master server.
      _topology (dict[str, set[str]]): A dictionary defining the connection topology
                                       between servers.
  """

  def __init__(self, topology: dict[ServerInfo, set[ServerInfo]], master_name: str, sock_pool_size: int):
    self._logger = server_logger.bind(server_name="CLUSTER_MANAGER")

    self._server_infos: dict[str, ServerInfo] = {}

    for from_, tos in topology.items():
      self._server_infos[from_.name] = from_
      for t in tos:
        self._server_infos[t.name] = t

    self._master_server_name = master_name

    self._topology = topology.copy()
    for si in self._server_infos.values():
      if si not in self._topology:
        self._topology[si] = set()

    self._servers = {}
    for si in self._server_infos.values():
      connection_stub = ConnectionStub(self._topology[si], sock_pool_size)
      self._servers[si.name] = self.create_server(si, connection_stub)

    self._logger.debug(
      f"Intialized Cluster with following configuration:-\n{self._topology}"
    )

  def create_server(self, si: ServerInfo, connection_stub: ConnectionStub) -> Server:
    return Server(info=si, connection_stub=connection_stub)

  def start_all(self):
    """Starts all the servers and creates connections according to the topology."""
    self._logger.info("Starting cluster")
    for s in self._servers.values():
      s.start()
    sleep(2)

  def stop_all(self):
    """Stop all the servers."""
    self._logger.info("Stopping cluster")

    for s in self._servers.values():
      s.kill()
    sleep(2)

  def remove_connections(self, connections: list[tuple[str, str]]):
    """"""
    for _from, to in connections:
      assert _from in self._servers, f"{_from} is not a server"
      assert to in self._servers, f"{to} is not a server"

  @property
  def master_info(self):
    return self._server_infos[self._master_server_name]
