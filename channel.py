from __future__ import division
import link
import select

SAFE_BANDWIDTH_PART = 0.8

class Channel:
    def __init__(self):
        self.links = []
        self.recv_callback = lambda x: None

    def send(self, data):
        link = self.choose_link()
        link.send(data)

    def choose_link(self):
        safe_links = [ l for l in self.links
          if l.used_bandwidth / l.calc_bandwidth > SAFE_BANDWIDTH_PART ]
        if safe_links:
            return min(safe_links, key=lambda l: l.calc_ping)
        else:
            return max(self.links,
              key=lambda l: self.calc_bandwidth - self.used_bandwidth)

    def loop(self, file, bufsize=4096):
        while True:
            r, _, _ = select.select(self.links + [file], [], [],
                                    timeout=link.STAT_INTERVAL / 2)
            for ready in r:
                if ready == file:
                    data = file.read(bufsize)
                    self.send(data)
                else:
                    ready.recv()

            for link in self.links:
                link.maybe_send_req()
