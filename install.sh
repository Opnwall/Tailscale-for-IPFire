#!/bin/bash
[ -n "${BASH_VERSION:-}" ] || exec /bin/bash "$0" "$@"
set -euo pipefail

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
LANG_MARKER="tailscale service_status"
TAILSCALE_ARCH="${TAILSCALE_ARCH:-${1:-}}"
DOWNLOAD_TMPDIR=""

print_step() {
    echo
    echo "==> $1"
}

die() {
    echo "Error: $1" >&2
    exit 1
}

cleanup() {
    if [[ -n "${DOWNLOAD_TMPDIR:-}" && -d "$DOWNLOAD_TMPDIR" ]]; then
        rm -rf "$DOWNLOAD_TMPDIR"
    fi
}
trap cleanup EXIT

assert_elf() {
    local file="$1"
    local name="$2"

    [[ -s "$file" ]] || die "$name is empty: $file"

    if [[ "$(head -c 4 "$file")" != $'\x7fELF' ]]; then
        die "$name is not a Linux ELF binary. Download the static build from https://pkgs.tailscale.com/stable/#static and replace $file."
    fi
}

require_file() {
    local file="$1"
    [[ -f "$file" ]] || die "Missing file: $file"
}

require_dir() {
    local dir="$1"
    [[ -d "$dir" ]] || die "Missing directory: $dir"
}

detect_tailscale_arch() {
    local machine

    machine="$(uname -m 2>/dev/null || true)"
    case "$machine" in
        x86_64|amd64)
            echo "amd64"
            ;;
        aarch64|arm64)
            echo "arm64"
            ;;
        armv5*|armv6*|armv7*|armhf|arm)
            echo "arm"
            ;;
        i386|i486|i586|i686)
            echo "386"
            ;;
        *)
            die "Unsupported platform architecture: ${machine:-unknown}. Set TAILSCALE_ARCH to amd64, arm64, arm, or 386."
            ;;
    esac
}

install_lang_fragment() {
    local src="$1"
    local dst="$2"
    local tmp
    local rc

    require_file "$src"
    require_file "$dst"

    tmp="$(mktemp /tmp/tailscale-lang.XXXXXX)"

    set +e
    perl -0e '
        use strict;
        use warnings;

        my ($src, $dst, $tmp, $marker) = @ARGV;

        open(my $sfh, "<:raw", $src) or die "open $src failed: $!";
        my $fragment = <$sfh>;
        close($sfh);
        $fragment =~ s/\A\s+//;
        $fragment =~ s/\s+\z/\n/;

        open(my $dfh, "<:raw", $dst) or die "open $dst failed: $!";
        my $data = <$dfh>;
        close($dfh);

        sub find_final_hash_terminator {
            my ($text) = @_;
            my $pos = -1;

            while ($text =~ /^[ \t]*\);[ \t]*(?:#.*)?(?:\r?\n|\z)/mg) {
                $pos = $-[0];
            }

            return $pos;
        }

        my $close_pos = find_final_hash_terminator($data);
        die "$dst has no final language hash terminator\n" if $close_pos < 0;

        my $marker_pos = index($data, $marker);
        if ($marker_pos >= 0 && $marker_pos < $close_pos) {
            open(my $ofh, ">:raw", $tmp) or die "open $tmp failed: $!";
            print {$ofh} $data;
            close($ofh);
            exit 2;
        }

        if ($marker_pos >= 0) {
            $data =~ s/\r?\n# Tailscale add-on\r?\n.*?(?=^[ \t]*\);[ \t]*(?:#.*)?(?:\r?\n|\z))//sm;
            $close_pos = find_final_hash_terminator($data);
            die "$dst has no final language hash terminator after cleanup\n" if $close_pos < 0;
        }

        my $insert = "\n# Tailscale add-on\n" . $fragment;
        $insert .= "\n" unless $insert =~ /\n\z/;

        substr($data, $close_pos, 0) = $insert;

        open(my $ofh, ">:raw", $tmp) or die "open $tmp failed: $!";
        print {$ofh} $data;
        close($ofh);
    ' "$src" "$dst" "$tmp" "$LANG_MARKER"
    rc=$?
    set -e

    if [[ $rc -eq 2 ]]; then
        rm -f "$tmp"
        echo "Language entries already present in $dst"
        return 0
    fi

    if [[ $rc -ne 0 ]]; then
        rm -f "$tmp"
        die "Failed to update language file: $dst"
    fi

    install -m 644 "$tmp" "$dst"
    rm -f "$tmp"
    echo "Added language entries to $dst"
}

install_language_entries() {
    install_lang_fragment ./langs/lang.en /var/ipfire/langs/en.pl
    install_lang_fragment ./langs/lang.zh /var/ipfire/langs/zh.pl
    install_lang_fragment ./langs/lang.tw /var/ipfire/langs/tw.pl
}

download_tailscale_binaries() {
    local url="https://pkgs.tailscale.com/stable/tailscale_latest_${TAILSCALE_ARCH}.tgz"
    local pkg_dir

    case "$TAILSCALE_ARCH" in
        amd64|arm|arm64|386) ;;
        *) die "Unsupported architecture: $TAILSCALE_ARCH. Supported values: amd64, arm, arm64, 386" ;;
    esac

    command -v curl >/dev/null 2>&1 || die "curl is required"
    command -v tar >/dev/null 2>&1 || die "tar is required"

    DOWNLOAD_TMPDIR="$(mktemp -d /tmp/tailscale-static.XXXXXX)"

    echo "Downloading Tailscale static package: $url"
    curl -fL "$url" -o "$DOWNLOAD_TMPDIR/tailscale.tgz"

    echo "Extracting Tailscale static package"
    tar -xzf "$DOWNLOAD_TMPDIR/tailscale.tgz" -C "$DOWNLOAD_TMPDIR"

    pkg_dir="$(find "$DOWNLOAD_TMPDIR" -maxdepth 1 -type d -name 'tailscale_*' | head -n 1)"
    [[ -n "$pkg_dir" ]] || die "Could not find extracted Tailscale directory"
    [[ -x "$pkg_dir/tailscale" ]] || die "tailscale is missing from the static package"
    [[ -x "$pkg_dir/tailscaled" ]] || die "tailscaled is missing from the static package"

    install -d -m 755 ./bin
    install -m 755 "$pkg_dir/tailscale" ./bin/tailscale
    install -m 755 "$pkg_dir/tailscaled" ./bin/tailscaled

    assert_elf ./bin/tailscale "tailscale"
    assert_elf ./bin/tailscaled "tailscaled"
}

if [[ $EUID -ne 0 ]]; then
    die "Please run this script as root."
fi

cd "$BASE_DIR"

if [[ -z "$TAILSCALE_ARCH" ]]; then
    TAILSCALE_ARCH="$(detect_tailscale_arch)"
fi

print_step "Preparing Tailscale installation"
echo "This will install tailscale, tailscaled, the Web UI, the menu entry, language strings, and reload the Web service."
echo "Tailscale static binary architecture: $TAILSCALE_ARCH"
read -r -p "Continue? (y/N): " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Operation cancelled."
    exit 0
fi

print_step "Checking source files"
for dir in ./ipfire ./cgi-bin ./etc ./langs; do
    require_dir "$dir"
done

require_file ./etc/init.d/tailscale
require_file ./cgi-bin/tailscale.cgi
require_file ./langs/lang.en
require_file ./langs/lang.zh
require_file ./langs/lang.tw

print_step "Downloading Tailscale binaries"
download_tailscale_binaries

print_step "Creating target directories"
install -d -m 755 /var/ipfire/tailscale
install -d -m 755 /srv/web/ipfire/cgi-bin
install -d -m 755 /usr/local/bin
install -d -m 755 /usr/sbin
install -d -m 755 /etc/sudoers.d
install -d -m 755 /var/run/tailscale

print_step "Copying files"
tmp_settings=""
if [[ -f /var/ipfire/tailscale/settings ]]; then
    tmp_settings="$(mktemp /tmp/tailscale-settings.backup.XXXXXX)"
    cp -p /var/ipfire/tailscale/settings "$tmp_settings"
fi

cp -a ./ipfire/. /var/ipfire/
cp -a ./cgi-bin/. /srv/web/ipfire/cgi-bin/
install -m 755 ./etc/init.d/tailscale /etc/init.d/tailscale
install -m 755 ./bin/tailscale /usr/local/bin/tailscale
install -m 755 ./bin/tailscaled /usr/sbin/tailscaled

if [[ -n "$tmp_settings" && -f "$tmp_settings" ]]; then
    install -m 644 "$tmp_settings" /var/ipfire/tailscale/settings
    rm -f "$tmp_settings"
fi

print_step "Setting permissions"
chmod 755 /etc/init.d/tailscale
chmod 755 /usr/local/bin/tailscale
chmod 755 /usr/sbin/tailscaled
chmod 755 /srv/web/ipfire/cgi-bin/tailscale.cgi
chmod 755 /var/ipfire/tailscale
chmod 644 /var/ipfire/tailscale/settings
[[ -f /var/ipfire/tailscale/state ]] || touch /var/ipfire/tailscale/state
chmod 644 /var/ipfire/tailscale/state

touch /var/log/tailscale.log
chmod 644 /var/log/tailscale.log

print_step "Verifying installation"
[[ -x /etc/init.d/tailscale ]] || die "tailscale init script is missing or not executable"
[[ -x /usr/local/bin/tailscale ]] || die "tailscale CLI is missing or not executable"
[[ -x /usr/sbin/tailscaled ]] || die "tailscaled is missing or not executable"
[[ -f /srv/web/ipfire/cgi-bin/tailscale.cgi ]] || die "tailscale.cgi was not installed"

print_step "Configuring startup"
ln -sf /etc/init.d/tailscale /etc/rc.d/rc3.d/S99tailscale

print_step "Configuring sudo permissions"
cat > /etc/sudoers.d/tailscale <<'EOF'
nobody ALL=(ALL) NOPASSWD: /etc/init.d/tailscale
nobody ALL=(ALL) NOPASSWD: /usr/local/bin/tailscale
nobody ALL=(ALL) NOPASSWD: /usr/sbin/tailscaled
EOF
chmod 440 /etc/sudoers.d/tailscale
visudo -cf /etc/sudoers.d/tailscale >/dev/null || die "sudoers validation failed"

print_step "Installing language entries"
install_language_entries

print_step "Rebuilding language cache"
perl -e "require '/var/ipfire/lang.pl'; Lang::BuildCacheLang();" || die "Failed to rebuild language cache"

print_step "Adding forwarding rules"
iptables -C FORWARD -i tailscale0 -j ACCEPT 2>/dev/null || iptables -A FORWARD -i tailscale0 -j ACCEPT
iptables -C FORWARD -o tailscale0 -j ACCEPT 2>/dev/null || iptables -A FORWARD -o tailscale0 -j ACCEPT
grep -q '^net.ipv4.ip_forward=1$' /etc/sysctl.conf || echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf
sysctl -w net.ipv4.ip_forward=1 >/dev/null

print_step "Reloading Web service"
/etc/init.d/apache reload >/dev/null 2>&1 || true

echo
echo "Tailscale installation complete."
echo "Go to the Web UI (Services > Tailscale), save the settings, and join the network."
