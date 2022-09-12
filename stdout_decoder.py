from typing import List


class StdOutDecoder:
    def __init__(self):
        self.lines: List[List[str]] = []
        self.row = 0
        self.col = 0

    def print(self, text: str):
        for char in text:
            if char == '\n':
                self.col = 0
                self.row += 1
            elif char == '\r':
                self.col = 0
            elif char == '\b':
                self.col -= 1
            else:
                self._set(self.row, self.col, char)
                self.col += 1

    def _set(self, row, col, char):
        while row > len(self.lines):
            self.lines.append([])

        if row >= len(self.lines):
            self.lines.append([char])
        elif col >= len(self.lines[row]):
            self.lines[row].append(char)
        else:
            self.lines[row][col] = char

    def __str__(self):
        return '\n'.join(''.join(x) for x in self.lines)


if __name__ == '__main__':
    import subprocess
    import threading
    import time

    command = ['ffplay', '-i',
               'concat:'
               '/home/elisha/Videos/Test/AVCHD/BDMV/STREAM/00000.MTS|'
               '/home/elisha/Videos/Test/AVCHD/BDMV/STREAM/00001.MTS|'
               '/home/elisha/Videos/Test/AVCHD/BDMV/STREAM/00002.MTS|'
               '/home/elisha/Videos/Test/AVCHD/BDMV/STREAM/00003.MTS|'
               '/home/elisha/Videos/Test/AVCHD/BDMV/STREAM/00004.MTS|'
               '/home/elisha/Videos/Test/AVCHD/BDMV/STREAM/00005.MTS|'
               '/home/elisha/Videos/Test/AVCHD/BDMV/STREAM/00006.MTS|'
               '/home/elisha/Videos/Test/AVCHD/BDMV/STREAM/00007.MTS|'
               '/home/elisha/Videos/Test/AVCHD/BDMV/STREAM/00008.MTS']

    dec = StdOutDecoder()


    def command_output_loop(proc: subprocess.Popen):
        print("starting loop")
        pipe = proc.stderr
        # l = []
        while process.poll() is None:
            char = pipe.read(1)
            # print(char)
            if char != b'':
                dec.print(char.decode())
                # print(str(dec))
                # l.append(char.decode())
                # if char in (b'\n', b'\r'):
                #     dec.print(''.join(l))
                #     l = []
        rest = pipe.read()
        dec.print(rest.decode())


    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output_thread_stdout = threading.Thread(target=command_output_loop, args=[process])
    output_thread_stdout.start()

    time.sleep(10)
    process.terminate()
    print(str(dec).replace('\r', '\\r'))
