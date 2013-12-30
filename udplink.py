import socket

MAX_UDP_SIZE = 4096

class UdpLinkImpl:
    def __init__(self, local, remote, sock=None):
        self.recv_callback = lambda x: None
        if sock:
            self.sock = sock
        else:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET,
                                 socket.SO_REUSEADDR, 1)
            self.sock.bind(local)
        self.local = self.sock.getsockname()
        self.remote = remote

    def send(self, data):
        self.sock.sendto(data, self.remote)

    def fileno(self):
        return self.sock.fileno()

    def recv(self):
        data, addr = self.sock.recvfrom(MAX_UDP_SIZE)
        self.recv_data(data)

    def recv_data(self, data):
        self.recv_callback(data)

def parse_addr(s):
    host, port = s.rsplit(':', 1)
    return host, int(port)
