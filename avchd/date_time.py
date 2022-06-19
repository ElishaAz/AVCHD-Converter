import datetime

DATE_LENGTH = 0x7


def decode_date_digit(d: int):
    return (d >> 4) * 10 + (d & 0xf)


def decode_date(data: bytes) -> datetime.datetime:
    year = decode_date_digit(data[0]) * 100 + decode_date_digit(data[1])
    month = decode_date_digit(data[2])
    day = decode_date_digit(data[3])
    hour = decode_date_digit(data[4])
    minute = decode_date_digit(data[5])
    second = decode_date_digit(data[6])
    return datetime.datetime(year, month, day, hour, minute, second)
