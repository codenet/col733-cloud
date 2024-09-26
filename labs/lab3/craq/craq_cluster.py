import random
from typing import Optional, Final

from core.cluster import ClusterManager
from core.network import TcpClient, ConnectionStub
from core.server import ServerInfo, Server

START_PORT: Final[int] = 9900

class CraqClient():
  # TODO: Implement this class
  pass


class CraqCluster(ClusterManager):
  def __init__(self) -> None:
    # TODO: Initialize the cluster
    pass

  def connect(self) -> CraqClient:
    # TODO: Implement this method
    pass

  def create_server(self, si: ServerInfo, connection_stub: ConnectionStub) -> Server:
    # TODO: Implement this method
    pass
