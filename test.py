import channel
import udplink

import sys
import fcntl
import os

os.dup2(1, 2)
fcntl.fcntl(sys.stdin, fcntl.F_SETFL, os.O_NONBLOCK)

class File:
    def read(self, size):
        return sys.stdin.read(size)

    def write(self, data):
        print repr(data)[:10]

    def fileno(self):
        return sys.stdin.fileno()

def parse_addr(s):
    host, port = s.rsplit(':', 1)
    return host, int(port)

ch = channel.Channel()
ch.add_link(udplink.UdpLinkImpl(
    parse_addr(sys.argv[1]),
    parse_addr(sys.argv[2])))

ch.loop(File())
