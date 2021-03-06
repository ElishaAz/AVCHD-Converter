HEADER_ITEMS = 0x41
HEADER_SEQUENCE_INFO_OFFSET = (0x0C, 0x0C + 4)
HEADER_PLEX_OFFSET = (0x10, 0x10 + 4)

A_OFFSET = 0x44
A_ITEM_LENGTH = 0x62
A_SPANNING = 0xB
A_START_TIME = 0xE
A_END_TIME = 0x12

B_HEADER_LENGTH = 0x6
B_ITEMS = 0x5
B_ITEM_LENGTH = 0xE
B_PLAYLIST_NUMBER = 0x1
B_STARTING_CLIP = 0x3

C_TITLE = b"PLEX"
C_HEADER_LENGTH = 0x146
C_HEADER_DATE = 0x33
C_ITEMS = 0x145
C_ITEM_LENGTH = 0x42
C_ITEM_DATE = 0xB
C_ITEM_UNKNOWN = 0x3C
