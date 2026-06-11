<div align="center">
    <div align="center"> 中文 | <a href="README.en-US.md">English</div>
</div>


# Tailscale for IPFire

![IPFire](https://img.shields.io/badge/IPFire-2.29-orange)
![Architecture](https://img.shields.io/badge/Arch-x86__64-blue)
![License](https://img.shields.io/badge/License-GPLv3-green)

适用于 IPFire 的 Tailscale VPN 集成插件，提供原生 Web UI 管理界面支持。

![Screenshot](image/tailscale.png)

## 项目概述

Tailscale for IPFire 为 IPFire 提供原生 Web 管理界面，可直接在 IPFire 管理后台中完成 Tailscale 的配置与管理。

安装过程中会自动下载官方 Tailscale 静态二进制文件，并支持：

- 子网路由（Subnet Router）
- 出口节点（Exit Node）
- 多语言 Web UI

## 功能特性

- 原生 IPFire Web UI 集成
- 使用 Auth Key 加入 Tailscale 网络
- 自定义主机名
- 发布子网路由
- 支持 Exit Node（出口节点）
- 自动识别平台架构
- 自动下载官方 Tailscale 静态二进制文件
- 支持英文、简体中文和繁体中文

## 测试平台

| 平台 | 版本 |
|------|------|
| IPFire | 2.29 Core Update 202 |
| 架构 | x86_64 / amd64 |

## 安装

```bash
sh install.sh
```

## 卸载

```bash
sh uninstall.sh
```

## 配置

安装完成后进入：

```text
Services > Tailscale
```

配置以下项目：

- Auth Key（认证密钥）
- Hostname（主机名）
- Advertise Routes（发布路由）
- Exit Node 设置

然后点击：

```text
Join Network
```

## 命令行使用

启动 Tailscale：

```bash
/etc/init.d/tailscale up
```

## 子网路由（Subnet Router）

发布内部网段，例如：

```text
192.168.101.0/24
```

或者执行：

```bash
tailscale up --advertise-routes=192.168.101.0/24 --accept-dns=false --accept-routes --hostname=ipfire
```

完成后：

1. 打开 Tailscale Admin Console
2. 选择对应的 IPFire 设备
3. 启用 Subnet Routes

## 出口节点（Exit Node）

在 Web UI 中启用 Exit Node，或执行：

```bash
tailscale up --advertise-exit-node --accept-dns=false --accept-routes --advertise-routes=192.168.101.0/24 --hostname=ipfire
```

随后在 Tailscale Admin Console 中批准：

```text
Use as exit node
```

## Tailscale 二进制文件

安装程序会自动下载官方静态二进制文件：

https://pkgs.tailscale.com/stable/#static

## 注意事项

- 建议使用 Auth Key 进行自动部署。
- 发布路由后需要在 Tailscale 管理后台手动批准。
- Exit Node 同样需要在管理后台批准。
- 默认禁用 DNS 接管（`--accept-dns=false`），避免覆盖 IPFire 本地 DNS 配置。

## 许可证

GPLv3

## 免责声明

本项目为社区维护的非官方软件包。

与以下组织不存在任何隶属、授权或官方支持关系：

- IPFire
- Tailscale

使用风险由用户自行承担。
