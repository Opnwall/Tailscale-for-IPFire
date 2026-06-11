# Tailscale for IPFire

![IPFire](https://img.shields.io/badge/IPFire-2.29-orange)
![Architecture](https://img.shields.io/badge/Arch-x86__64-blue)
![License](https://img.shields.io/badge/License-GPLv3-green)

Tailscale VPN integration for IPFire with native Web UI support.

![Screenshot](image/tailscale.png)

## Overview

Tailscale for IPFire provides a native Web UI for managing Tailscale directly from the IPFire administration interface.

The package automatically downloads the official Tailscale static binaries during installation and supports subnet routing, exit node functionality, and multilingual Web UI integration.

## Features

- Native IPFire Web UI integration
- Join Tailscale networks using Auth Keys
- Configure custom hostnames
- Advertise subnet routes
- Enable Exit Node functionality
- Automatic platform detection
- Automatic download of official Tailscale static binaries
- English, Simplified Chinese, and Traditional Chinese language support

## Tested Platforms

| Platform | Version |
|----------|----------|
| IPFire | 2.29 Core Update 202 |
| Architecture | x86_64 / amd64 |

## Installation

```bash
sh install.sh
```

## Uninstallation

```bash
sh uninstall.sh
```

## Configuration

After installation, open:

```text
Services > Tailscale
```

Configure:

- Auth Key
- Hostname
- Advertise Routes
- Exit Node settings

Then click:

```text
Join Network
```

## Command Line Usage

Bring up Tailscale:

```bash
/etc/init.d/tailscale up
```

## Subnet Router

To advertise an internal subnet:

```text
192.168.101.0/24
```

Or use:

```bash
tailscale up --advertise-routes=192.168.101.0/24 --accept-dns=false --accept-routes --hostname=ipfire
```

After advertising routes:

1. Open the Tailscale Admin Console
2. Select the IPFire device
3. Enable Subnet Routes

## Exit Node

Enable Exit Node in the Web UI or run:

```bash
tailscale up --advertise-exit-node --accept-dns=false --accept-routes --advertise-routes=192.168.101.0/24 --hostname=ipfire
```

Then approve:

```text
Use as exit node
```

in the Tailscale Admin Console.

## Tailscale Binaries

The installer downloads official static binaries from:

https://pkgs.tailscale.com/stable/#static

## Notes

- Auth Keys are recommended for automated deployment.
- Advertised routes must be approved in the Tailscale Admin Console.
- Exit Nodes must also be approved in the Admin Console.
- DNS management is disabled by default (`--accept-dns=false`) to avoid overriding local IPFire DNS settings.

## License

GPLv3

## Disclaimer

This project is an unofficial community package.

It is not affiliated with, endorsed by, or supported by:

- IPFire
- Tailscale

Use at your own risk.
