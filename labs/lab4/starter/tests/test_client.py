import time
from typing import Literal
from unittest import TestCase

from bayou.app import BayouAppClient
from bayou.cluster import BayouClusterManager
from bayou.ctrlmsg import WriteState
from core.message import JsonMessage
from core.server import ServerInfo


def assert_write(
    response: JsonMessage, status: Literal["OK", "Err"], write_state: WriteState
):
    return response["status"] == status and response["write_state"] == write_state.name


def assert_read(
    response: JsonMessage, status: Literal["OK", "Err"], committed: str, tentative: str
):
    return (
        response["status"] == status
        and response["committed"] == committed
        and response["tentative"] == tentative
    )


class TestStringAppenderClient(TestCase):
    def setUp(self) -> None:
        start_port = 10005
        self.s1 = ServerInfo("s1", start_port)
        self.s2 = ServerInfo("s2", start_port + 1)
        topology = {self.s1: {self.s2}, self.s2: {self.s1}}
        self.cluster = BayouClusterManager(topology, "s1")

        self.cluster.start_all()

    def test(self) -> None:
        client_s1 = BayouAppClient(self.s1)
        client_s2 = BayouAppClient(self.s2)

        client_s1.sever_conn("s2")
        client_s2.sever_conn("s1")

        response = client_s1.append_char("a")
        self.assertTrue(assert_write(response, "OK", WriteState.COMMITTED))

        response = client_s2.append_char("b")
        self.assertTrue(assert_write(response, "OK", WriteState.TENTATIVE))

        # Give time to fail anti-entropy on sever conn
        time.sleep(2)
        response = client_s1.get_string()
        self.assertTrue(assert_read(response, "OK", "a", "a"))

        response = client_s2.get_string()
        self.assertTrue(assert_read(response, "OK", "", "b"))

        client_s1.unsever_conn("s2")
        client_s2.unsever_conn("s1")

        # Give time to perform anti-entropy
        time.sleep(2)
        response = client_s1.get_string()
        self.assertTrue(assert_read(response, "OK", "ab", "ab"))

        response = client_s2.get_string()
        self.assertTrue(assert_read(response, "OK", "ab", "ab"))

    def tearDown(self) -> None:
        self.cluster.stop_all()


# TODO (Optional):- Write more tests
