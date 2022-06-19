import datetime
from typing import List

from avchd.clip import Clip


class Sequence:
    def __init__(self, date: datetime.datetime, clips: List[Clip]):
        self.date: datetime.datetime = date
        self.clips: List[Clip] = clips

    def __str__(self):
        return F"Sequence({self.date}, [{', '.join(str(c) for c in self.clips)}]"
