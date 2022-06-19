"""
A lot of the code is based on
https://forum.videohelp.com/threads/296805-Reading-AVCHD-Playlist-files-BDMV-Playlist-%2A-mpl and
http://www.eiman.tv/misc/flashdump.txt
"""
from avchd.clip import Clip
from avchd.date_time import DATE_LENGTH, decode_date
from avchd.playlist import Playlist
from avchd.positions import *
from avchd.sequence import Sequence


class Decoder:

    def __init__(self, file: str):
        self.data: bytes
        with open(file, mode="rb") as file:
            self.data = file.read()
        self.header = self._decode_header()
        self.section_a = self._decode_section_a()
        self.section_b = self._decode_section_b()
        self.section_c_plex = self._decode_section_c_plex()

    def _decode_header(self):
        return {
            "count": self.data[HEADER_ITEMS],
            "sequence_info_offset":
                int.from_bytes(self.data[HEADER_SEQUENCE_INFO_OFFSET[0]: HEADER_SEQUENCE_INFO_OFFSET[1]]
                               , "big", signed=False),
            "PLEX_offset": int.from_bytes(self.data[HEADER_PLEX_OFFSET[0]:HEADER_PLEX_OFFSET[1]], "big",
                                          signed=False) + 0x18
        }

    def _decode_section_a(self):
        clips = []

        pos = A_OFFSET
        for x in range(self.header["count"]):
            clip = self._decode_clip_a(self.data[pos:pos + A_ITEM_LENGTH])
            clips.append(clip)
            pos += A_ITEM_LENGTH

        return {"clips": clips, "end_pos": pos}

    @staticmethod
    def _decode_clip_a(data):
        return {
            "name": data[2:11].decode(),
            "filename": data[2:7].decode(),
            "type": data[-4:-1].decode(),
            "start": int.from_bytes(data[A_START_TIME:A_START_TIME + 4], "big", signed=False),
            "end": int.from_bytes(data[A_END_TIME:A_END_TIME + 4], "big", signed=False),
            "spanning": data[A_SPANNING] == 6
        }

    def _decode_section_b(self):
        offset = self.section_a["end_pos"]

        assert offset == self.header["sequence_info_offset"]

        count = self.data[offset + B_ITEMS]
        sequences = []

        pos = offset + B_HEADER_LENGTH
        for i in range(count):
            sequences.append(self._decode_sequence_b(self.data[pos:pos + B_ITEM_LENGTH]))
            pos += B_ITEM_LENGTH

        return {"count": count, "sequences": sequences, "end_pos": pos}

    @staticmethod
    def _decode_sequence_b(data):
        return {"playlist_number": data[B_PLAYLIST_NUMBER], "starting_clip": data[B_STARTING_CLIP]}

    def _decode_section_c_plex(self):
        offset = self.header["PLEX_offset"]
        assert offset == self.section_b["end_pos"] + 24
        assert self.data[offset:offset + len(C_TITLE)] == C_TITLE

        offset += len(C_TITLE)
        date = decode_date(self.data[offset + C_HEADER_DATE:offset + C_HEADER_DATE + DATE_LENGTH])
        count = self.data[offset + C_ITEMS]

        sequences = []
        pos = offset + C_HEADER_LENGTH
        for i in range(count):
            sequences.append(self._decode_sequence_c_plex(self.data[pos:pos + C_ITEM_LENGTH]))
            pos += C_ITEM_LENGTH

        return {"date": date, "count": count, "sequences": sequences, "end_pos": pos}

    @staticmethod
    def _decode_sequence_c_plex(data):
        date = decode_date(data[C_ITEM_DATE:C_ITEM_DATE + DATE_LENGTH])
        unknown = int.from_bytes(data[C_ITEM_UNKNOWN:C_ITEM_UNKNOWN + 4], "big")
        return {"date": date, "unknown": unknown}

    def to_playlist(self) -> Playlist:
        clips = []
        for i in range(self.header["count"]):
            clip = self.section_a["clips"][i]
            clips.append(Clip(clip["filename"], clip["start"], clip["end"]))

        sequences = []
        for i in range(self.section_b["count"]):
            sequence_b = self.section_b["sequences"][i]
            starting_clip = sequence_b["starting_clip"]
            if i + 1 >= len(self.section_b["sequences"]):
                end_clip = len(clips)
            else:
                end_clip = self.section_b["sequences"][i + 1]["starting_clip"]
            sequence_c = self.section_c_plex["sequences"][i]
            sequences.append(Sequence(sequence_c["date"], clips[starting_clip:end_clip]))

        playlist = Playlist(self.section_c_plex["date"], sequences)

        return playlist


if __name__ == '__main__':
    p = Decoder("00002.MPL")
    print(p.to_playlist())
