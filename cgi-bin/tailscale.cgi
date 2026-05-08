#!/usr/bin/perl
use strict;
use warnings;
use utf8;
use JSON::PP;

require '/var/ipfire/general-functions.pl';
require "${General::swroot}/lang.pl";
require "${General::swroot}/header.pl";

my %settings = ();

# ====== 可调整路径 ======
my $service        = "/etc/init.d/tailscale";
my $sudo_cmd       = "/usr/bin/sudo";
# ========================

&Header::showhttpheaders();
&Header::getcgihash(\%settings);

my $action      = $settings{'ACTION'} || '';
my $cmd_output  = '';
my $show_output = 0;

sub run_service_command {
    my ($command) = @_;
    return `$sudo_cmd -n $service $command 2>&1`;
}

sub read_status_json {
    my $json_text = run_service_command('tsstatus_json');
    my $rc = $? >> 8;

    if ($rc == 0 && $json_text ne '') {
        my $data = eval { decode_json($json_text) };
        return $data if !$@ && ref($data) eq 'HASH';
    }

    return {};
}

sub get_connection_info {
    my $data        = read_status_json();
    my $status_text = run_service_command('tsstatus');
    my $ip_text     = run_service_command('ip');

    my %info = (
        hostname     => '',
        tailscale_ip => '',
        login_state  => '未登录',
        advertise_routes => '未设置',
        exit_node        => '否',
        peer_total   => 0,
        peer_online  => 0,
        peer_rows    => [],
    );

    my @ip_lines = grep { $_ ne '' && $_ !~ /not found/i && $_ !~ /socket/i } map { s/^\s+|\s+$//gr } split(/\n/, $ip_text);
    my ($ipv4_line) = grep { /^(?:\d{1,3}\.){3}\d{1,3}$/ } @ip_lines;
    if (defined $ipv4_line && $ipv4_line ne '') {
        $info{'tailscale_ip'} = $ipv4_line;
    }

    if (ref($data) eq 'HASH' && ref($data->{'Self'}) eq 'HASH') {
        my $self = $data->{'Self'};

        $info{'hostname'} = $self->{'HostName'} if defined $self->{'HostName'};

        if (ref($self->{'TailscaleIPs'}) eq 'ARRAY' && @{$self->{'TailscaleIPs'}}) {
            my ($ipv4_ip) = grep { /^(?:\d{1,3}\.){3}\d{1,3}$/ } @{$self->{'TailscaleIPs'}};
            if (defined $ipv4_ip && $ipv4_ip ne '') {
                $info{'tailscale_ip'} = $ipv4_ip;
            }
        }

        if (ref($self->{'AllowedIPs'}) eq 'ARRAY' && @{$self->{'AllowedIPs'}}) {
            my @routes = grep {
                defined $_
                && $_ ne ''
                && $_ !~ /\/32$/
                && $_ !~ /\/128$/
                && $_ !~ /^100\.64\.0\.0\/10$/
                && $_ !~ /^fd7a:115c:a1e0::\/48$/i
            } @{$self->{'AllowedIPs'}};
            if (@routes) {
                $info{'advertise_routes'} = join(', ', @routes);
            }
        }

        if ((defined $self->{'ExitNode'} && $self->{'ExitNode'}) ||
            (defined $self->{'ExitNodeOption'} && $self->{'ExitNodeOption'})) {
            $info{'exit_node'} = '是';
        }

        if ($self->{'Online'}) {
            $info{'login_state'} = '已连接';
        }
        elsif ($self->{'ID'}) {
            $info{'login_state'} = '已登录';
        }
        if ($info{'exit_node'} eq '否' && defined $status_text) {
            my $self_name = $info{'hostname'};
            for my $line (split(/\n/, $status_text)) {
                next if $line =~ /^\s*$/;
                if ($self_name ne '' && $line =~ /\b\Q$self_name\E\b/ && $line =~ /offers exit node/i) {
                    $info{'exit_node'} = '是';
                    last;
                }
            }
        }
    }

    if (ref($data) eq 'HASH' && ref($data->{'Peer'}) eq 'HASH') {
        my $peer = $data->{'Peer'};
        $info{'peer_total'} = scalar(keys %{$peer});

        for my $id (sort keys %{$peer}) {
            my $p = $peer->{$id};
            next unless ref($p) eq 'HASH';

            my $hostname = defined $p->{'HostName'} ? $p->{'HostName'} : '';
            my $ip = '';
            if (ref($p->{'TailscaleIPs'}) eq 'ARRAY' && @{$p->{'TailscaleIPs'}}) {
                $ip = $p->{'TailscaleIPs'}[0];
            }
            my $user = '';
            if (ref($data->{'User'}) eq 'HASH' && defined $p->{'UserID'} && exists $data->{'User'}->{$p->{'UserID'}}) {
                my $u = $data->{'User'}->{$p->{'UserID'}};
                if (ref($u) eq 'HASH' && defined $u->{'LoginName'}) {
                    $user = $u->{'LoginName'};
                }
            }
            my $state = $p->{'Online'} ? '在线' : '离线';

            push @{$info{'peer_rows'}}, {
                ip       => $ip,
                hostname => $hostname,
                user     => $user,
                state    => $state,
                online   => $p->{'Online'} ? 1 : 0,
            };

            $info{'peer_online'}++ if $p->{'Online'};
        }
    }
    else {
        for my $line (split(/\n/, $status_text)) {
            next if $line =~ /^\s*$/;
            next if $line =~ /^#\s*Health/i;
            next if $line =~ /^100\.64\.0\.1\s+/;

            my @parts = split(/\s+/, $line);
            next unless @parts >= 2;
            next unless $parts[0] =~ /^(?:\d{1,3}\.){3}\d{1,3}$/ || $parts[0] =~ /:/;

            my $ip = shift @parts;
            my $hostname = shift @parts;
            my $user = @parts ? $parts[0] : '';
            my $state = '在线';

            $info{'peer_total'}++;
            $info{'peer_online'}++;

            push @{$info{'peer_rows'}}, {
                ip       => $ip,
                hostname => $hostname,
                user     => $user,
                state    => $state,
                online   => 1,
            };
        }
    }

    return %info;
}

# ====== 动作处理 ======
if ($action eq 'start') {
    $cmd_output = run_service_command('start');
    $show_output = 1;
}
elsif ($action eq 'stop') {
    $cmd_output = run_service_command('stop');
    $show_output = 1;
}
elsif ($action eq 'restart') {
    $cmd_output = run_service_command('restart');
    $show_output = 1;
}
elsif ($action eq 'down') {
    $cmd_output = run_service_command('down');
    $show_output = 1;
}
elsif ($action eq 'refresh') {
    $cmd_output = "状态已刷新";
    $show_output = 1;
}

# ====== 状态读取 ======
my $service_check = run_service_command('status');
my $running = (($? >> 8) == 0 || $service_check =~ /running/i) ? 1 : 0;
my %conn = get_connection_info();

# ====== 页面 ======
&Header::openpage("Tailscale", 1, '');
print "<meta charset='UTF-8'>\n";
print <<'EOF';
<style>
.status-dot {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    margin-right: 6px;
    vertical-align: middle;
}
.status-dot.running {
    background: #2ecc71;
}
.status-dot.stopped {
    background: #e74c3c;
}
.info-table {
    width: 100%;
    border-collapse: collapse;
}
.info-table td {
    padding: 6px 8px;
    border-bottom: 1px solid #ddd;
    vertical-align: top;
}
.info-table td.key {
    width: 180px;
    font-weight: bold;
    color: #333;
    background: #f7f7f7;
}
.peer-table {
    width: 100%;
    border-collapse: collapse;
}
.peer-table th,
.peer-table td {
    padding: 6px 8px;
    border-bottom: 1px solid #ddd;
    text-align: left;
    vertical-align: top;
}
.peer-table th {
    background: #f7f7f7;
    color: #333;
    font-weight: bold;
}
.peer-online {
    color: #2ecc71;
    font-weight: bold;
}
.peer-offline {
    color: #e74c3c;
    font-weight: bold;
}
.ipfire-note {
    margin-top: 8px;
    padding: 6px 8px;
    border: 1px solid #ddd;
    background: #f7f7f7;
    color: #333;
}
.ipfire-note.success {
    border-color: #b7d7a8;
    background: #edf8e5;
    color: #2f5d12;
}
</style>
EOF

&Header::openbigbox('100%', 'left', '', '');
print "<form method='post'>";

# ====== 服务状态 ======
&Header::openbox('100%', 'left', '服务状态');

print "<b>状态:</b> ";
if ($running) {
    print "<span class='status-dot running'></span><span style='color:green;'>运行中</span>";
}
else {
    print "<span class='status-dot stopped'></span><span style='color:red;'>已停止</span>";
}

print "<br><br>";

print "<button type='submit' name='ACTION' value='start'>启动</button>  ";
print "<button type='submit' name='ACTION' value='stop'>停止</button>  ";
print "<button type='submit' name='ACTION' value='restart'>重启</button>  ";
print "<button type='submit' name='ACTION' value='refresh'>刷新</button>  ";

if ($show_output) {
    print "<br><br>";
    if ($action eq 'refresh') {
        print "<div class='ipfire-note success'>状态已刷新</div>";
    }
    else {
        print "<div class='ipfire-note'>";
        print &Header::escape($cmd_output);
        print "</div>";
    }
}

&Header::closebox();

# ====== 连接信息 ======
&Header::openbox('100%', 'left', '连接信息');

print "<table class='info-table'>";
print "<tr><td class='key'>主机名称</td><td>" . &Header::escape($conn{'hostname'}) . "</td></tr>";
print "<tr><td class='key'>分配地址</td><td>" . &Header::escape($conn{'tailscale_ip'}) . "</td></tr>";
print "<tr><td class='key'>登录状态</td><td>" . &Header::escape($conn{'login_state'}) . "</td></tr>";
print "<tr><td class='key'>通告路由</td><td>" . &Header::escape($conn{'advertise_routes'}) . "</td></tr>";
print "<tr><td class='key'>出口节点</td><td>" . &Header::escape($conn{'exit_node'}) . "</td></tr>";
print "<tr><td class='key'>远程节点</td><td>" . &Header::escape($conn{'peer_total'}) . "</td></tr>";
print "<tr><td class='key'>在线节点</td><td>" . &Header::escape($conn{'peer_online'}) . "</td></tr>";
print "</table>";

&Header::closebox();

# ====== 节点信息 ======
&Header::openbox('100%', 'left', '节点信息');

print "<table class='peer-table'>";
print "<tr><th>Tailscale IP</th><th>主机名</th><th>用户</th><th>状态</th></tr>";

if (ref($conn{'peer_rows'}) eq 'ARRAY' && @{$conn{'peer_rows'}}) {
    for my $peer (@{$conn{'peer_rows'}}) {
        my $ip = defined $peer->{'ip'} ? $peer->{'ip'} : '';
        my $hostname = defined $peer->{'hostname'} ? $peer->{'hostname'} : '';
        my $user = defined $peer->{'user'} ? $peer->{'user'} : '';
        my $state = defined $peer->{'state'} ? $peer->{'state'} : '';
        my $state_class = $peer->{'online'} ? 'peer-online' : 'peer-offline';

        print "<tr>";
        print "<td>" . &Header::escape($ip) . "</td>";
        print "<td>" . &Header::escape($hostname) . "</td>";
        print "<td>" . &Header::escape($user) . "</td>";
        print "<td class='$state_class'>" . &Header::escape($state) . "</td>";
        print "</tr>";
    }
}
else {
    print "<tr><td colspan='4'>暂无节点信息</td></tr>";
}

print "</table>";

&Header::closebox();

print "\n";
print "</form>";

&Header::closebigbox();
&Header::closepage();