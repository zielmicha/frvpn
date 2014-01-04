from __future__ import division
import select
import time
import socket

import link
import udplink

SAFE_BANDWIDTH_PART = 0.8

class Channel:
    def __init__(self):
        self.links = []
        self.link_impls = []
        self.link_impl_by_remote = {}
        self.recv_callback = lambda x: None
        self._info_print = 0

    def add_link(self, impl):
        self.link_impls.append(impl)
        self.links.append(link.Link(impl, self._recv))
        self.link_impl_by_remote[impl.remote] = impl

    def _recv(self, data):
        self.recv_callback(data)

    def send(self, data):
        link = self.choose_link()
        link.send(data)

    def choose_link(self):
        return min(self.links, key=lambda l: l.expected_arrival_time)

    def _print_info(self):
        if self._info_print + 1 < time.time():
            self._info_print = time.time()
            print self.links

    def client_loop(self, file, bufsize=4096):
        self.recv_callback = file.write

        while True:
            r, _, _ = select.select(self.link_impls + [file], [], [],
                                    link.STAT_INTERVAL / 2)
            self._print_info()
            for ready in r:
                if ready == file:
                    data = file.read(bufsize)
                    self.send(data)
                else:
                    ready.recv()

            for l in self.links:
                l.maybe_send_req()

class ChannelServer(Channel):
    def server_loop(self, file, addr, bufsize=4096):
        self.recv_callback = file.write
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(addr)

        while True:
            r, _, _ = select.select([file, sock], [], [],
                                    link.STAT_INTERVAL / 2)
            self._print_info()
            if file in r:
                data = file.read(bufsize)
                self.send(data)
            elif sock in r:
                data, remote_addr = sock.recvfrom(bufsize)
                #print 'recv', repr(data), remote_addr
                impl = self.get_or_create_impl(addr, remote_addr, sock)
                impl.recv_data(data)

            for l in self.links:
                l.maybe_send_req()

    def get_or_create_impl(self, local, remote, sock):
        if remote not in self.link_impl_by_remote:
            print 'Create link (remote:%s local:%s)' % (remote, local)
            impl = udplink.UdpLinkImpl(local, remote, sock=sock)
            self.add_link(impl)

        return self.link_impl_by_remote[remote]
