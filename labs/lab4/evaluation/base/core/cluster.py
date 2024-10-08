import abc
from time import sleep

from .logger import server_logger
from .network import ConnectionStub
from .server import Server, ServerInfo


class ClusterManager:
  """
  This class manages a cluster of Bayou servers. It is responsible for starting
  servers and establishing connections between them according to a specified topology.

  Attributes:
      _topology (dict[str, set[str]]): A dictionary defining the connection topology
                                       between servers.
  """

  def __init__(self, topology: dict[ServerInfo, set[ServerInfo]]):
    self._logger = server_logger.bind(server_name="CLUSTER_MANAGER")

    self._server_infos: dict[str, ServerInfo] = {}

    for from_, tos in topology.items():
      self._server_infos[from_.name] = from_
      for t in tos:
        self._server_infos[t.name] = t

    self._topology = topology.copy()
    for si in self._server_infos.values():
      if si not in self._topology:
        self._topology[si] = set()

    self._servers = {}
    for si in self._server_infos.values():
      connection_stub = ConnectionStub(self._topology[si])
      self._servers[si.name] = self.create_server(si, connection_stub)

    self._logger.debug(
      f"Intialized Cluster with following configuration:-\n{self._topology}"
    )

  @abc.abstractmethod
  def create_server(self, si: ServerInfo, connection_stub: ConnectionStub) -> Server:
    pass

  def start_all(self) -> None:
    """Starts all the servers and creates connections according to the topology."""
    self._logger.info("Starting cluster")
    for s in self._servers.values():
      s.start()
    sleep(2)

  def stop_all(self) -> None:
    """Stop all the servers."""
    self._logger.info("Stopping cluster")

    for s in self._servers.values():
      s.kill()
    sleep(2)
