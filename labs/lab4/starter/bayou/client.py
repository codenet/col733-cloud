from core.message import JsonMessage
from core.network import TcpClient
from core.server import ServerInfo
from bayou.ctrlmsg import BayouResponse, RequestTypes


class BayouClient:
  def __init__(self, to: ServerInfo):
    self._conn = TcpClient(to)

  def _send(self, js: JsonMessage) -> JsonMessage:
    response = self._conn.send(js)
    assert response is not None
    return response

  def sever_conn(self, peer_name: str) -> JsonMessage:
    return self._send(JsonMessage(msg={"peer_name": peer_name, "type": RequestTypes.SEVER_CONN.name}))

  def unsever_conn(self, peer_name: str) -> JsonMessage:
    return self._send(JsonMessage(msg={"peer_name": peer_name, "type": RequestTypes.UNSEVER_CONN.name}))
