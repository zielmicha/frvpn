from __future__ import division
from blist import blist
import time
import struct
import collections

KB = 1000
MB = 1000 * KB
INF = float('inf')

PACKET_DATA = '\x01'
PACKET_STAT_REQ = '\x02'
PACKET_STAT = '\x03'
#PACKET_STAT_ACK = '\x04'

BANDWIDTH_PROBE_TIME = 1
BANDWIDTH_SCALE = 0.99
BANDWIDTH_SCALE_INTERVAL = 1
STAT_INTERVAL = 0.5
STAT_AVG_COUNT = 4

_Stat = collections.namedtuple('_Stat', 'num ping quality')

class _LinkSender:
    '''
    Implements sending side of link.
    '''
    def __init__(self, impl):
        self.impl = impl
        # reasonable defaults
        self.calc_ping = 0.1
        self.calc_bandwidth = 100 * KB
        self.calc_quality = 1
        self._last_bandwidth_scale = time.time()

        # use 64-bit integer to never run out of packet_nums
        self.packet_num = 0
        self.last_packet_num = 0
        self.stat_num = 0
        self.last_packets = blist()
        self._used_bandwidth = 0
        self._stats = blist()

    def get_used_bandwidth(self):
        # Amortized time O(log n)
        curr = time.time()
        oldest_time = curr - BANDWIDTH_PROBE_TIME
        while (self.last_packets and
               self.last_packets[0][0] < oldest_time):
            ptime, plen = self.last_packets.pop(0)
            self._used_bandwidth -= ptime
        return self._used_bandwidth / BANDWIDTH_PROBE_TIME

    used_bandwidth = property(get_used_bandwidth)

    def send(self, data):
        self.last_packets.append((time.time(), len(data)))
        self._used_bandwidth += len(data)
        header = PACKET_DATA
        header += struct.pack('!Q', self.packet_num)
        self.packet_num += 1
        self.impl.send(header + data)
        self._recalc()

    def _send_req(self):
        pack = PACKET_STAT_REQ
        pack += struct.pack('!QdQQ', self.stat_num, time.time(),
                            self.packet_num, self.last_packet_num)
        self.last_packet_num = self.packet_num
        self.stat_num += 1
        self.impl.send(pack)

    def _recv_stat(self, data):
        stat_num, quality, send_time = struct.unpack('!xQdd', data)
        recv_time = time.time()
        ping = send_time - recv_time
        self._stats.append(_Stat(stat_num, ping, quality))
        self._recalc()

    def _recalc(self):
        oldest_num = self.stat_num - STAT_AVG_COUNT
        while (self._stats and
               self._stats[0].num < oldest_num):
            self._stats.pop(0)

        if self._stats:
            self.calc_ping = avg( stat.ping
                for stat in self._stats)
            self.calc_quality = avg( stat.quality
                for stat in self._stats)
            self._recalc_bandwidth()
        else:
            self.calc_bandwidth = 0
            self.calc_ping = INF

    def _recalc_bandwidth(self):
        # This method relies on higher level flow
        # control (TCP, for example) being used.
        # Decreases calc_bandwidth only if there is packet
        # loss AND link is congested.
        # Increases always when managed to send more data
        # that current estimate (TCP flow control algorithm
        # tries to do that every few seconds).
        self._scale_bandwidth()
        throughtput = self.calc_quality * self.used_bandwidth
        if throughtput > self.calc_bandwidth:
            self.calc_bandwidth = throughtput
        else:
            # If link was not congested don't decrease bandwidth
            # TODO: multiply by some constant?
            if self.used_bandwidth > self.calc_bandwidth:
                self.calc_bandwidth = throughtput

    def _scale_bandwidth(self):
        # Decrease bandwidth a bit, so if TCP flow control
        # by chance detects quality loss before us, we won't
        # stay with too large calc_bandwidth.
        # If link quality has not decreased _recalc_bandwidth
        # will increase it back.
        t = self._last_bandwidth_scale - time.time()
        count = int(t // BANDWIDTH_SCALE_INTERVAL)
        self._last_bandwidth_scale += count * BANDWIDTH_SCALE_INTERVAL
        self.calc_bandwidth *= (BANDWIDTH_SCALE ** count)

def avg(s):
    return sum(s) / len(s)

class _LinkRecv:
    def __init__(self, impl, recv_callback):
        self.impl = impl
        self.recv_callback = recv_callback

        self.packet_nums = []

    def _recv_req(self, data):
        stat_num, send_time, \
            end_num, start_num = struct.pack('!xQdQQ', data)
        quality = self._calc_quality(start_num, end_num)
        self._send_stat(stat_num, quality, send_time)

    def _calc_quality(self, start, end):
        count = end - start
        if count < 5:
            # traffic too small
            return 1.
        else:
            success = 0
            for i in packet_nums:
                if start <= i <= end:
                    success += 1
            self.packet_nums = []
            return success / count

    def _send_stat(self, stat_num, quality, send_time):
        packet = PACKET_STAT
        packet += struct.pack('!Qdd', stat_num, quality, send_time)
        self.send(packet)

    def _recv_packet(self, data):
        packet_num, = struct.unpack('!Q', data[1:9])
        body = data[9:]

        self.recv_callback(body)
