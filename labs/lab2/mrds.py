from __future__ import annotations
from typing import Final
import redis
from constants import FNAME

class MyRedis:
  def __init__(self):
    self.rds: Final = redis.Redis(host='localhost', port=6379, db=0, decode_responses=False)
    self.rds.flushall()

  def add_file(self, stream_name: bytes, fname: str, id: int):
    self.rds.xadd(stream_name, {FNAME: fname}, id=f"{id}-0")

