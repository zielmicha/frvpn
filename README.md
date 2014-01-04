# Fast Redundant VPN

FRVPN is in early stage of development.

## Usage

Server:

    python server.py [--tun devname] 0.0.0.0:[port]

Client:

    python client.py [--tun devname] 0.0.0.0:[local port]+[remote ip]:[remote port]
