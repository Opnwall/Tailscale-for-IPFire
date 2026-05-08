#!/bin/bash
set -euo pipefail

print_step() {
    echo
    echo "==> $1"
}

die() {
    echo "错误：$1" >&2
    exit 1
}

if [[ $EUID -ne 0 ]]; then
    die "请使用 root 运行此脚本。"
fi

print_step "准备安装 tailscale"
echo "该操作将安装 tailscale、tailscaled、Web 管理页面、菜单入口，并重载 Web 服务。"
read -r -p "是否继续？(y/N): " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "操作已取消。"
    exit 0
fi

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$BASE_DIR"

print_step "检查安装目录"
for dir in ./ipfire ./cgi-bin ./etc ./bin; do
    [[ -d "$dir" ]] || die "缺少目录 $dir"
done

[[ -f ./etc/init.d/tailscale ]] || die "缺少文件 ./etc/init.d/tailscale"
[[ -f ./cgi-bin/tailscale.cgi ]] || die "缺少文件 ./cgi-bin/tailscale.cgi"
[[ -f ./bin/tailscale ]] || die "缺少文件 ./bin/tailscale"
[[ -f ./bin/tailscaled ]] || die "缺少文件 ./bin/tailscaled"

print_step "创建必要目录"
install -d -m 755 /var/ipfire/tailscale
install -d -m 755 /srv/web/ipfire/cgi-bin
install -d -m 755 /usr/local/bin
install -d -m 755 /usr/sbin
install -d -m 755 /etc/sudoers.d
install -d -m 755 /var/run/tailscale

print_step "复制文件"
cp -a ./ipfire/. /var/ipfire/
cp -a ./cgi-bin/. /srv/web/ipfire/cgi-bin/
install -m 755 ./etc/init.d/tailscale /etc/init.d/tailscale
install -m 755 ./bin/tailscale /usr/local/bin/tailscale
install -m 755 ./bin/tailscaled /usr/sbin/tailscaled

print_step "设置文件权限"
chmod 755 /etc/init.d/tailscale
chmod 755 /usr/local/bin/tailscale
chmod 755 /usr/sbin/tailscaled
chmod 755 /srv/web/ipfire/cgi-bin/tailscale.cgi

[[ -d /var/ipfire/tailscale ]] || install -d -m 755 /var/ipfire/tailscale
[[ -f /var/ipfire/tailscale/settings ]] || touch /var/ipfire/tailscale/settings
[[ -f /var/ipfire/tailscale/state ]] || touch /var/ipfire/tailscale/state
chmod 755 /var/ipfire/tailscale
chmod 644 /var/ipfire/tailscale/settings
chmod 644 /var/ipfire/tailscale/state

touch /var/log/tailscale.log
chmod 644 /var/log/tailscale.log

print_step "检查安装结果"
[[ -x /etc/init.d/tailscale ]] || die "tailscale init 脚本不存在或不可执行"
[[ -x /usr/local/bin/tailscale ]] || die "tailscale CLI 不存在或不可执行"
[[ -x /usr/sbin/tailscaled ]] || die "tailscaled 不存在或不可执行"
[[ -f /srv/web/ipfire/cgi-bin/tailscale.cgi ]] || die "tailscale.cgi 未安装"

print_step "配置开机自启"
ln -sf /etc/init.d/tailscale /etc/rc.d/rc3.d/S99tailscale

print_step "配置 sudo 权限"
cat > /etc/sudoers.d/tailscale <<'EOF'
nobody ALL=(ALL) NOPASSWD: /etc/init.d/tailscale
nobody ALL=(ALL) NOPASSWD: /usr/local/bin/tailscale
nobody ALL=(ALL) NOPASSWD: /usr/sbin/tailscaled
EOF
chmod 440 /etc/sudoers.d/tailscale
visudo -cf /etc/sudoers.d/tailscale >/dev/null || die "sudoers 配置校验失败"

print_step "添加规则"
iptables -C FORWARD -i tailscale0 -j ACCEPT 2>/dev/null || iptables -A FORWARD -i tailscale0 -j ACCEPT
iptables -C FORWARD -o tailscale0 -j ACCEPT 2>/dev/null || iptables -A FORWARD -o tailscale0 -j ACCEPT
grep -q '^net.ipv4.ip_forward=1$' /etc/sysctl.conf || echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf
sysctl -w net.ipv4.ip_forward=1 >/dev/null

print_step "重载 Web 服务"
    /etc/init.d/apache reload >/dev/null 2>&1 || true

echo
echo "Tailscale 安装完成！"
echo "请在终端使用命令：/etc/init.d/tailscale up 来启动服务，连接到您的 Tailscale 网络。"
echo "然后前往 Web 界面（服务 > Tailscale）查看连接信息。"