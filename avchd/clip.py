class Clip:
    def __init__(self, name: str, start: int, end: int):
        self.name = name
        self.start = start
        self.end = end

    def __str__(self):
        return F"Clip({self.name})"

    def get_path(self, content_root):
        return
