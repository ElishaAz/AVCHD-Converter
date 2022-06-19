#!/usr/bin/env python

import sys
import struct


def split_byte(ch):
    byte = ch
    return [byte >> 4, byte & 0x0f]


def parse_date(data):
    ords = []
    for x in data:
        ords += split_byte(x)
    s = "".join(map(lambda x: chr(x + b'0'), ords))

    return "%s-%s-%s %s:%s:%s" % (s[0:4], s[4:6], s[6:8], s[8:10], s[10:12], s[12:])


def hex(data):
    hexes = "0123456789abcdef"
    s = ""
    for x in data:
        byte = data
        s += hexes[byte >> 4]
        s += hexes[byte & 0x0f]
    return s


def bin(data):
    s = ""
    for x in data:
        byte = data
        for i in range(8):
            if byte & (1 << 7 - i):
                s += "1"
            else:
                s += "0"
    return s


def decode_CA(data, files):
    if data[0:4] != [0x10, 0x11, 0x30, 0x00]:
        print(F"Bad CA header: {data[0:4]}")
        sys.exit(1)

    if data[44:46] != b"CA":
        print("Bad CA marker")
        sys.exit(1)

    # next two bytes after CA tells you the bitrate, probably

    ca = {
        "index": data[9],
        "date": parse_date(data[11:18]),
        "files": []
    }

    index = 0
    for f in files:
        if not f["spanning"]:
            index += 1
        if index - 1 == ca["index"]:
            # this file is used
            ca["files"].append(f)

    print("CA index %s date %s (files: %s)" % (ca["index"], ca["date"], map(lambda x: x["filename"], ca["files"])))

    return ca


def decode_PLEX(data):
    # could it be short for "PlayList EXtra info"?
    if data[0:4] != b"PLEX":
        print("bad PLEX header: %s" % (map(hex, data[0:4])))
        sys.exit(1)

    plex = {
        "items": ord(data[-1]),
        "date": parse_date(data[0x37:0x37 + 7])
    }

    print("PLEX has %s items, date %s" % (plex["items"], plex["date"]))

    return plex


def decode_unknown1(data):
    if data[0:2] != [0x00, 0x00]:
        print("Bad unknown1 header: %s" % (map(ord, data[0:2])))
        sys.exit(1)

    unknown1 = {
        "items": data[4]
    }

    print("unknown1 has %s items" % (unknown1["items"]))

    return unknown1


def decode_fileitem(data):
    if data[0] != ord('`'):
        print(data)
        print(data[0], ord('`'))
        print("Bad PlayItem header")
        sys.exit(1)

    item = {
        "name": data[1:10],
        "filename": data[1:6],
        "type": data[-5:-1],
        "spanning": data[11] == chr(6),
        # next might be clip length? what timebase?
        "x-hex": " ".join(F"{x:0>2X}" for x in data[11:21]),
        "x-bin": map(bin, data[11:21])
    }

    print("File: %s (%s, spanning: %s) %s" % (item["name"], item["filename"], item["spanning"], item["x-hex"]))

    return item


def decode_filelist(data):
    if data[0:8] != b"MPLS0100":
        print("Bad playlist header")
        sys.exit(1)

    filelist = {
        "items": data[0x41],
        "unknown1_offset": struct.unpack(">l", data[0x0c:0x0c + 4])[0],
        "PLEX_offset": struct.unpack(">l", data[0x10:0x10 + 4])[0] + 0x18
    }

    print("File list with %s files" % (filelist["items"]))

    return filelist


def parse_file(path):
    print("Parsing %s" % (path))
    data = open(path, "rb").read()

    filelist = decode_filelist(data)

    # read items
    files = []
    pos = 0x45
    for x in range(filelist["items"]):
        # dump PlayItems
        fileitem = decode_fileitem(data[pos:pos + 0x52])
        files.append(fileitem)
        pos += 0x52 + 16

    # read unknown segment that's probably the start of the playlist
    unknown1 = decode_unknown1(data[pos:])

    # read PLEX segment
    plex = decode_PLEX(data[filelist["PLEX_offset"]:filelist["PLEX_offset"] + 0x14a])
    pos = filelist["PLEX_offset"] + 0x14a

    # read CA items
    for x in range(plex["items"]):
        ca = decode_CA(data[pos:pos + 0x42], files)
        pos += 0x42


if __name__ == "__main__":
    import sys

    parse_file("files/00002.MPL")
