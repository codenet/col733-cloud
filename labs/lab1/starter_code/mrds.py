from __future__ import annotations

import logging
from typing import Optional, Final

from redis.client import Redis

from base import Worker
from config import config


class MyRedis:
  def __init__(self):
    self.rds: Final = Redis(host='localhost', port=6379, password=None,
                       db=0, decode_responses=False)
    self.rds.flushall()
    self.rds.xgroup_create(config["IN"], Worker.GROUP, id="0", mkstream=True)

  def add_file(self, fname: str):
    self.rds.xadd(config["IN"], {config["FNAME"]: fname})

  def top(self, n: int) -> list[tuple[bytes, float]]:
    return self.rds.zrevrangebyscore(config["COUNT"], '+inf', '-inf', 0, n,
                                     withscores=True)

  def is_pending(self) -> bool:
    # TODO
    pass

  def restart(self, downtime: int):
    # TODO
    pass
