from typing import Optional

from cr.cr_server import CRServer
from core.cluster import ClusterManager
from core.message import JsonMessage, JsonMessage
from core.network import TcpClient, ConnectionStub
from core.server import ServerInfo, Server

POOL_SZ = 32

class CrClient:
  def __init__(self, infos: list[ServerInfo]):
    self.conns: list[TcpClient] = []
    for info in infos:
      conn = TcpClient(info)
      self.conns.append(conn)

  def set(self, key: str, val: str) -> bool:
    response: Optional[JsonMessage] = self.conns[0].send(JsonMessage({"type": "SET",
                                                                  "key": key,
                                                                  "val": val}))
    assert response is not None
    return response["status"] == "OK"

  def get(self, key: str) -> tuple[bool, Optional[str]]:
    response: Optional[JsonMessage] = self._get_server().send(JsonMessage({"type": "GET", "key": key}))
    assert response is not None
    if response["status"] == "OK":
      return True, response["val"]
    return False, response["status"]

  def _get_server(self) -> TcpClient:
    # Tail server
    return self.conns[-1]


class CrCluster(ClusterManager):
  def __init__(self) -> None:
    self.a = ServerInfo("a", "localhost", 9900)
    self.b = ServerInfo("b", "localhost", 9901)
    self.c = ServerInfo("c", "localhost", 9902)
    self.d = ServerInfo("d", "localhost", 9903)

    self.prev: dict[ServerInfo, Optional[ServerInfo]] = {
      self.a: None,
      self.b: self.a,
      self.c: self.b,
      self.d: self.c,
    }
    self.next: dict[ServerInfo, Optional[ServerInfo]] = {
      self.a: self.b,
      self.b: self.c,
      self.c: self.d,
      self.d: None,
    }

    super().__init__(
      master_name="d",
      topology={self.a: {self.b},
                self.b: {self.c},
                self.c: {self.d},
                self.d: set()},
      sock_pool_size=POOL_SZ,
    )

  def connect(self, craq: bool = False) -> CrClient:
    return CrClient([self.a, self.b, self.c, self.d])

  def create_server(self, si: ServerInfo, connection_stub: ConnectionStub) -> Server:
    return CRServer(info=si, connection_stub=connection_stub,
                      next=self.next[si], prev=self.prev[si], tail=self.d)
