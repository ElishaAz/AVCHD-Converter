import datetime
from typing import List

from avchd.sequence import Sequence


class Playlist:
    def __init__(self, date: datetime.datetime, sequences: List[Sequence]):
        self.date = date
        self.sequences = sequences

    def __str__(self):
        return F"Playlist({self.date}, [{', '.join(str(s) for s in self.sequences)}]"
