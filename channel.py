from __future__ import division
import link
import select

SAFE_BANDWIDTH_PART = 0.8

class Channel:
    def __init__(self):
        self.links = []
        self.link_impls = []
        self.recv_callback = lambda x: None

    def add_link(self, impl):
        self.link_impls.append(impl)
        self.links.append(link.Link(impl, self._recv))

    def _recv(self, data):
        self.recv_callback(data)

    def send(self, data):
        link = self.choose_link()
        link.send(data)

    def choose_link(self):
        safe_links = [ l for l in self.links
          if l.used_bandwidth_part < SAFE_BANDWIDTH_PART ]
        if safe_links:
            return min(safe_links, key=lambda l: l.calc_ping)
        else:
            return min(self.links,
                       key=lambda l: l.used_bandwidth_part)

    def loop(self, file, bufsize=4096):
        def callback(data):
            file.write(data)

        self.recv_callback = callback

        while True:
            r, _, _ = select.select(self.link_impls + [file], [], [],
                                    link.STAT_INTERVAL / 2)
            for ready in r:
                if ready == file:
                    data = file.read(bufsize)
                    self.send(data)
                else:
                    ready.recv()

            for l in self.links:
                l.maybe_send_req()
