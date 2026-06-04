## Tailscale for IPFire

Tailscale add-on for IPFire. Tested on IPFire 2.29 (x86_64), Core Update 202.

![](image/tailscale.png)

## Tailscale Binaries

The installer downloads the official [Tailscale static binaries](https://pkgs.tailscale.com/stable/#static) during installation. 

## Notes

The add-on is tested on x86_64 / amd64. The installer detects the IPFire platform automatically and downloads the matching Tailscale static binary. You can still override the architecture with `sh install.sh arm64`, `sh install.sh arm`, or `sh install.sh 386`.

The Web UI uses IPFire language packs and includes English, Simplified Chinese, and Traditional Chinese strings.

## Install

```bash
sh install.sh
```

To install for another architecture:

```bash
sh install.sh arm64
```

## Uninstall

```bash
sh uninstall.sh
```

## Setup

- After installation, go to Services > Tailscale, enter the auth key, hostname, and route settings, then click Join Network.
- You can also join from the terminal:

```bash
/etc/init.d/tailscale up
```

- To access an IPFire subnet from Tailscale, advertise the route. For example, enter this in Advertise Routes:

```text
192.168.101.0/24
```

Or run:

```bash
tailscale up --advertise-routes=192.168.101.0/24 --accept-dns=false --accept-routes --hostname=ipfire
```

- In the Tailscale admin console, open the IPFire device route settings and enable Subnet routes.
- To use IPFire as an exit node, enable Exit Node in the Web UI, or run:

```bash
tailscale up --advertise-exit-node --accept-dns=false --accept-routes --advertise-routes=192.168.101.0/24 --hostname=ipfire
```

- In the Tailscale admin console, open the IPFire device route settings and enable Use as exit node.
