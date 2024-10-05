from typing import Literal, override
from bayou.server import BayouServer
from bayou.app import BayouAppServer
from core.logger import server_logger
from core.cluster import ClusterManager
from core.network import ConnectionStub
from core.server import ServerInfo


class BayouClusterManager(ClusterManager):
    """
    This class manages a cluster of Bayou servers. It is responsible for starting
    servers and establishing connections between them according to a specified topology.

    Attributes:
        _master_server_name (str): The name of the master server.
        _topology (dict[str, set[str]]): A dictionary defining the connection topology
                                         between servers.
    """

    def __init__(
        self,
        topology: dict[ServerInfo, set[ServerInfo]],
        master_name: str,
        storage_type: Literal["app"] = "app",
    ):
        self._logger = server_logger.bind(server_name="CLUSTER_MANAGER")
        self._master_server_name = master_name

        self._peers = list(set().union(*topology.values()))
        self._peers.sort(key=lambda s: s.name)

        self._storage_type: Literal["app"] = storage_type

        super().__init__(topology)

    @property
    def master_info(self) -> ServerInfo:
        return self._server_infos[self._master_server_name]

    @override
    def create_server(
        self,
        si: ServerInfo,
        connection_stub: ConnectionStub,
    ) -> BayouServer:
        if self._storage_type == "app":
            return BayouAppServer(si, connection_stub, si.name == self._master_server_name, peers=self._peers)
        else:
            raise NotImplementedError(f"{self._storage_type} not implemented yet")
