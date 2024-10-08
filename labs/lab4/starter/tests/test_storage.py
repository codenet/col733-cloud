from __future__ import annotations

import time
from typing import cast
from unittest import TestCase

from sortedcontainers import SortedList  # type: ignore

from bayou.app import AppState, AppLogEntry
from bayou.storage import Storage, VectorTime, LogicalTime


class AbsStorageTest(TestCase):
  def setUp(self) -> None:
    self.servers: list[str] = ["s1", "s2"]
    self.storage = Storage(self.servers, AppState())

    self.time = time.monotonic_ns()
    self.ltime = LogicalTime("s1", self.time)
    self.ntime = VectorTime.new(self.servers)
    self.vtime = VectorTime([self.ltime, LogicalTime("s2")])

    self.write = AppLogEntry("a", self.ltime)

  def committed_st(self) -> AppState:
    return cast(AppState, self.storage.committed_st)

  def tentative_st(self) -> AppState:
    return cast(AppState, self.storage.tentative_st)

  def chk_invariants(self) -> None:
    self.storage.chk_invariants()

    committed = ""
    for w in self.storage.committed_log:
      tw = cast(AppLogEntry, w)
      committed += tw.char

    self.assertTrue(self.committed_st().s == committed)

    tentative = ""
    for w in self.storage.tentative_log:
      tw = cast(AppLogEntry, w)
      tentative += tw.char
    self.assertTrue(self.tentative_st().s == (committed + tentative))


class BasicStorageTest(AbsStorageTest):
  def test_vtime(self) -> None:
    self.assertEqual(self.vtime, VectorTime([self.ltime, LogicalTime("s2")]))

    self.assertTrue(self.vtime.is_ltime_earlier(LogicalTime("s1")))
    self.assertTrue(self.vtime.is_ltime_earlier(LogicalTime("s2")))
    # Notice that we are testing for "s2". vtime has a 1900s time for s2.
    self.assertFalse(self.vtime.is_ltime_earlier(LogicalTime("s2", self.time)))

    self.assertTrue(self.vtime.is_vtime_earlier(self.ntime))

  def __commit(self) -> None:
    self.storage.commit([self.write])
    # Commit writes to both tentative and commit state
    self.assertEqual(self.committed_st().s, "a")
    self.assertEqual(self.tentative_st().s, "a")

    # Commit adds to committed log, and not to tentative log
    self.assertListEqual(self.storage.committed_log, [self.write])
    self.assertEqual(self.storage.tentative_log, SortedList())

    # Commit advances both commit timestamp C and final timestamp F.
    self.assertEqual(self.storage.c, self.vtime)
    self.assertEqual(self.storage.f, self.vtime)

  def test_commit(self) -> None:
    self.__commit()
    # Commits are idempotent!
    self.__commit()
    self.chk_invariants()

  def __tentative(self) -> None:
    self.storage.tentative(SortedList([self.write]))
    # Tentative only writes to tentative state
    self.assertEqual(self.committed_st().s, "")
    self.assertEqual(self.tentative_st().s, "a")

    # Tentative adds to tentative log, and not to committed log
    self.assertListEqual(self.storage.committed_log, [])
    self.assertEqual(self.storage.tentative_log, SortedList([self.write]))

    # Tentative only advances final timestamp F
    self.assertEqual(self.storage.c, self.ntime)
    self.assertEqual(self.storage.f, self.vtime)

    self.chk_invariants()

  def test_tentative(self) -> None:
    self.__tentative()
    # Tentatives are idempotent!
    self.__tentative()
    self.chk_invariants()

class AntiEntropyTest(AbsStorageTest):
  def setUp(self) -> None:
    super().setUp()
    time.sleep(0.01)

    self.later_time = time.monotonic_ns()
    self.later_ltime = LogicalTime("s2", self.later_time)
    self.later_vtime = VectorTime([self.ltime, self.later_ltime])

  def test_commit_anti_entropy(self) -> None:
    self.storage.commit([self.write])

    # Should get some committed log with an older commit timestamp
    committed, tentative = self.storage.anti_entropy(self.ntime, self.ntime)
    self.assertListEqual(committed, [self.write])
    self.assertEqual(tentative, SortedList())

    # Should NOT get a committed log with a newer commit timestamp
    committed, tentative = self.storage.anti_entropy(self.later_vtime, self.ntime)
    self.assertListEqual(committed, [])
    self.assertEqual(tentative, SortedList())

    # Error if we try to get committed log with a commit timestamp that is neither older nor newer
    self.assertRaises(AssertionError, self.storage.anti_entropy,
                      VectorTime([LogicalTime("s1"), self.later_ltime]), self.later_vtime)

  def test_tentative_anti_entropy(self) -> None:
    self.storage.tentative(SortedList([self.write]))

    # Should get some tentative log with an older final timestamp
    committed, tentative = self.storage.anti_entropy(self.ntime, self.ntime)
    self.assertListEqual(committed, [])
    self.assertEqual(tentative, SortedList([self.write]))

    # Should NOT get tentative log with a newer final timestamp
    committed, tentative = self.storage.anti_entropy(self.later_vtime, self.later_vtime)
    self.assertListEqual(committed, [])
    self.assertEqual(tentative, SortedList())

    # Tentative logs can be out of order. We will get some tentative logs if we send a final
    # timestamp that is neither older nor newer
    committed, tentative = self.storage.anti_entropy(self.later_vtime,
                                                     VectorTime([LogicalTime("s1"), self.later_ltime]))
    self.assertListEqual(committed, [])
    self.assertEqual(tentative, SortedList([self.write]))


# TODO (Optional): Write more tests 
