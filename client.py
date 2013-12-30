import argparse
import pytun
import channel
import udplink

parser = argparse.ArgumentParser()
parser.add_argument('--tun', metavar='name')
parser.add_argument('links', nargs='+')

args = parser.parse_args()

tun = pytun.TunTapDevice(**dict(name=args.tun)
                         if args.tun else {})

ch = channel.Channel()
for link in args.links:
    local, remote = link.split('+')
    ch.add_link(udplink.UdpLinkImpl(
        udplink.parse_addr(local),
        udplink.parse_addr(remote)))

ch.client_loop(tun)
