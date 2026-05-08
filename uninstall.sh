#!/bin/bash
# tailscale 卸载脚本
set -euo pipefail

print_step() {
    echo
    echo "==> $1"
}

if [[ $EUID -ne 0 ]]; then
    echo "错误：请使用 root 运行此脚本。" >&2
    exit 1
fi

print_step "准备卸载 tailscale"
echo "该操作将删除 tailscale 程序、Web 管理页面、启动项、运行文件和配置文件。"
read -r -p "是否继续？(y/N): " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "操作已取消。"
    exit 0
fi

print_step "停止 tailscale 服务"
    /etc/init.d/tailscale stop >/dev/null 2>&1 || true

print_step "移除开机自启"
rm -f /etc/rc.d/rc3.d/S99tailscale

print_step "删除程序文件"
rm -f /etc/init.d/tailscale
rm -f /usr/local/bin/tailscale
rm -f /usr/sbin/tailscaled
rm -f /srv/web/ipfire/cgi-bin/tailscale.cgi
rm -f /var/ipfire/menu.d/83-tailscale.menu

print_step "删除运行文件"
rm -rf /var/run/tailscale
rm -f /var/log/tailscale.log
rm -f /etc/sudoers.d/tailscale

print_step "删除配置文件"
rm -rf /var/ipfire/tailscale

print_step "重载 Web 服务"
    /etc/init.d/apache reload >/dev/null 2>&1 || true

echo
echo "tailscale 卸载完成！"