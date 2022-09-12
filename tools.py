import os
import subprocess
from typing import List, Optional, Iterable

from avchd import decoder
from avchd.sequence import Sequence
import platform

FFMPEG_COMMAND = "ffmpeg"
FFPLAY_COMMAND = "ffplay"

CONTENT_ROOT = ["PRIVATE", "AVCHD"]

STREAMS_IN_CONTENT_ROOT = ["BDMV", "STREAM"]
STREAM_EXT = ".MTS"

PLAYLISTS_IN_CONTENT_ROOT = ["BDMV", "PLAYLIST"]
PLAYLIST_EXT = ".MPL"


def get_content_root(drive: str) -> Optional[str]:
    if not os.path.exists(drive):
        return None
    content_root = os.path.join(drive, *CONTENT_ROOT)
    if not os.path.exists(content_root):
        return None
    playlists = os.path.join(content_root, *PLAYLISTS_IN_CONTENT_ROOT)
    if not os.path.exists(playlists):
        return None
    return content_root


def get_playlists(content_root: str) -> Optional[List[str]]:
    playlists_path = os.path.join(content_root, *PLAYLISTS_IN_CONTENT_ROOT)
    if not os.path.exists(playlists_path):
        return None

    playlists = []
    for f in os.listdir(playlists_path):
        file = os.path.join(playlists_path, f)
        if os.path.isfile(file) and file.endswith(PLAYLIST_EXT):
            playlists.append(file)

    playlists.sort()
    return playlists


def read_playlist(mpl_file: str):
    content: bytes
    with open(mpl_file, mode="rb") as file:
        content = file.read()

    files = []
    starts = []
    ends = []

    i = 0
    while i < len(content):
        index = content.find(b'`', i)
        if index == -1:
            break
        i = index + 1
        index += 1
        filename = content[index:index + 5].decode()
        index += 4

        index += 8

        start_bytes = content[index:index + 4]
        index += 4
        start = int.from_bytes(start_bytes, "big")
        end_bytes = content[index:index + 4]
        index += 4
        end = int.from_bytes(end_bytes, "big")

        print(filename, start, end)

        files.append(filename)

    return files


def create_concat(content_root: str, files: Iterable[str]):
    content_root = os.path.join(content_root, *STREAMS_IN_CONTENT_ROOT)
    return "|".join(os.path.join(content_root, f) + STREAM_EXT for f in files)


def preview_sequence(content_root: str, seq: Sequence) -> List[str]:
    return preview_command(create_concat(content_root, (x.name for x in seq.clips)))


def preview_command(concat_files) -> List[str]:
    return [FFPLAY_COMMAND, '-i', F"concat:{concat_files}"]


def convert_command(concat_files, output_file: str,
                    video_codec: Optional[str] = "copy",
                    audio_codec: Optional[str] = None) -> List[str]:
    command = [FFMPEG_COMMAND, '-i', F"concat:{concat_files}"]

    if video_codec is not None:
        command += ["-c:v", video_codec]

    if audio_codec is not None:
        command += ["-c:a", audio_codec]

    command.append(output_file)
    command.append('-y')

    return command


def convert_sequence(content_root: str, seq: Sequence, output_file: str,
                     video_codec: Optional[str] = "copy",
                     audio_codec: Optional[str] = None):
    return convert_command(create_concat(content_root, (x.name for x in seq.clips)), output_file, video_codec,
                           audio_codec)


def run_command(command: List[str]):
    subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def external_drives() -> List[str]:
    system = platform.system()
    if system == "Linux":
        d = F"/media/{os.getlogin()}"
        return [os.path.join(d, f) for f in os.listdir(d)]
    if system == "Windows":
        import string
        return ['%s:' % d for d in string.ascii_uppercase if os.path.exists('%s:' % d)]
    if system == "Darwin":
        return [F"/Volumes/{f}" for f in os.listdir('/Volumes')]

# if __name__ == '__main__':
# content_root = "/home/elisha/Videos/Test/AVCHD"
# playlists = get_playlists(content_root)
# print(playlists)
# filelist = read_playlist(playlists[3])
# print(filelist)
# print(create_concat(content_root, filelist))

# data = playlist.read(playlists[3])
# print(playlist.decode_header(data))
