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

    def test1(self) -> None:
        client_s1 = BayouAppClient(self.s1)
        client_s2 = BayouAppClient(self.s2)

        client_s1.sever_conn("s2")
        client_s2.sever_conn("s1")

        response = client_s1.append_char("a")
        self.assertTrue(assert_write(response, "OK", WriteState.COMMITTED))

        response = client_s2.append_char("b")
        self.assertTrue(assert_write(response, "OK", WriteState.TENTATIVE))

        # Give time to fail anti-entropy on sever conn
        time.sleep(6)
        response = client_s1.get_string()
        self.assertTrue(assert_read(response, "OK", "a", "a"))

        response = client_s2.get_string()
        self.assertTrue(assert_read(response, "OK", "", "b"))

        client_s1.unsever_conn("s2")
        client_s2.unsever_conn("s1")

        # Give time to perform anti-entropy
        time.sleep(6)
        response = client_s1.get_string()
        self.assertTrue(assert_read(response, "OK", "ab", "ab"))

        response = client_s2.get_string()
        self.assertTrue(assert_read(response, "OK", "ab", "ab"))

    def tearDown(self) -> None:
        self.cluster.stop_all()


# More tests to be added during evaluation

class TestStringAppenderClient2(TestCase):
    def setUp(self) -> None:
        start_port = 10005
        self.master = ServerInfo("master", start_port)
        self.s2 = ServerInfo("s2", start_port + 1)
        self.s3 = ServerInfo("s3", start_port + 2)
        topology = {
            self.master: {self.s2, self.s3},
            self.s2: {self.master, self.s3},
            self.s3: {self.s2, self.master},
        }
        self.cluster = BayouClusterManager(topology, "master")

        self.cluster.start_all()

        self.client_master = BayouAppClient(self.master)
        self.client_s2 = BayouAppClient(self.s2)
        self.client_s3 = BayouAppClient(self.s3)

        self.client_master.sever_conn("s3")
        self.client_s3.sever_conn("master")
        self.client_master.sever_conn("s2")
        self.client_s2.sever_conn("master")
        self.client_s2.sever_conn("s3")
        self.client_s3.sever_conn("s2")

    def test2(self) -> None:

        self.client_s2.unsever_conn("s3")
        self.client_s3.unsever_conn("s2")

        response = self.client_s2.append_char("a")
        self.assertTrue(assert_write(response, "OK", WriteState.TENTATIVE))
        
        response = self.client_s3.append_char("b")
        self.assertTrue(assert_write(response, "OK", WriteState.TENTATIVE))

        response = self.client_master.append_char("c")
        self.assertTrue(assert_write(response, "OK", WriteState.COMMITTED))

        # Wait for anit-entropy between s2 and s3
        time.sleep(1)
        response = self.client_master.get_string()
        print(response)
        self.assertTrue(assert_read(response, "OK", "c", "c"))

        response = self.client_s2.get_string()
        self.assertEqual(response["status"], "OK")
        self.assertTrue(assert_read(response, "OK", "", "ab"))

        response = self.client_s3.get_string()
        self.assertEqual(response["status"], "OK")
        self.assertTrue(assert_read(response, "OK", "", "ab"))

        self.client_master.unsever_conn("s2")
        self.client_s2.unsever_conn("master")

        # Give time to perform anti-entropy
        time.sleep(1)
        response = self.client_master.get_string()
        self.assertTrue(assert_read(response, "OK", "cab", "cab"))

        response = self.client_s2.get_string()
        self.assertTrue(assert_read(response, "OK", "cab", "cab"))

        response = self.client_s3.get_string()
        self.assertTrue(assert_read(response, "OK", "cab", "cab"))
    
    def test3(self) -> None:
        self.client_master.unsever_conn("s2")
        self.client_s2.unsever_conn("master")

        # master ----- s2 ------X----- s3

        response = self.client_s2.append_char("a")
        self.assertTrue(assert_write(response, "OK", WriteState.TENTATIVE))

        response = self.client_master.append_char("b")
        self.assertTrue(assert_write(response, "OK", WriteState.COMMITTED))

        response = self.client_s3.append_char("c")
        self.assertTrue(assert_write(response, "OK", WriteState.TENTATIVE))

        time.sleep(1)

        response = self.client_s2.get_string()
        self.assertEqual(response["status"], "OK")
        self.assertTrue(assert_read(response, "OK", "ba", "ba") or assert_read(response, "OK", "ab", "ab"))

        response = self.client_s3.get_string()
        self.assertEqual(response["status"], "OK")
        self.assertTrue(assert_read(response, "OK", "", "c"))

        self.client_master.unsever_conn("s3")
        self.client_s3.unsever_conn("master")

        time.sleep(1)

        response = self.client_s3.get_string()
        self.assertEqual(response["status"], "OK")
        self.assertTrue(assert_read(response, "OK", "bac", "bac") or assert_read(response, "OK", "abc", "abc"))
    


    def tearDown(self) -> None:
        self.cluster.stop_all()
