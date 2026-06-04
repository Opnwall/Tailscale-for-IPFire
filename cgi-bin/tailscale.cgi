#!/usr/bin/perl
use strict;
use warnings;
no warnings 'once';
use utf8;
use JSON::PP;
use File::Temp qw(tempfile);

require '/var/ipfire/general-functions.pl';
require "${General::swroot}/lang.pl";
require "${General::swroot}/header.pl";

my %settings = ();

# Adjustable paths.
my $service        = "/etc/init.d/tailscale";
my $sudo_cmd       = "/usr/bin/sudo";
my $settings_file  = "/var/ipfire/tailscale/settings";
# =================

&Header::showhttpheaders();
&Header::getcgihash(\%settings);

my $action      = $settings{'ACTION'} || '';
my $cmd_output  = '';
my $show_output = 0;
my $notice_type = 'success';
my $notice_text = '';
my %fallback = (
    not_logged_in => 'Not logged in',
    not_set => 'Not set',
    yes => 'Yes',
    no => 'No',
    connected => 'Connected',
    logged_in => 'Logged in',
    online => 'Online',
    offline => 'Offline',
    service_started => 'Service started.',
    service_start_failed => 'Failed to start service. Please check system logs.',
    service_stopped => 'Service stopped.',
    service_stop_failed => 'Failed to stop service. Please check system logs.',
    service_restarted => 'Service restarted.',
    service_restart_failed => 'Failed to restart service. Please check system logs.',
    config_saved => 'Settings saved.',
    joined => 'Joined Tailscale network with auth key.',
    join_failed => 'Failed to join network. Please check auth key, network connectivity, and Tailscale service status.',
    disconnected => 'Tailscale connection disconnected.',
    disconnect_failed => 'Failed to disconnect. Please check service status.',
    resumed => 'Tailscale connection restored.',
    resume_failed => 'Failed to restore connection. Please check the saved auth key, network connectivity, and Tailscale service status.',
    logged_out => 'Left Tailscale network.',
    logout_failed => 'Failed to leave network. Please check service status.',
    refreshed => 'Status refreshed.',
    service_status => 'Service Status',
    status => 'Status',
    running => 'Running',
    stopped => 'Stopped',
    start => 'Start',
    stop => 'Stop',
    restart => 'Restart',
    disconnect => 'Disconnect',
    resume => 'Restore Connection',
    refresh => 'Refresh',
    runtime_config => 'Runtime Settings',
    auth_key => 'Auth Key',
    auth_key_help => 'Used to authenticate and join the Tailscale network automatically.',
    hostname => 'Hostname',
    accept_routes => 'Accept Routes',
    accept_dns => 'Accept DNS',
    exit_node => 'Exit Node',
    advertise_routes => 'Advertise Routes',
    extra_args => 'Extra Arguments',
    save_config => 'Save Settings',
    join_network => 'Join Network',
    leave_network => 'Leave Network',
    connection_info => 'Connection Info',
    assigned_address => 'Assigned Address',
    login_state => 'Login State',
    peer_total => 'Peers',
    peer_online => 'Online Peers',
    peer_info => 'Peer Info',
    tailscale_ip => 'Tailscale IP',
    user => 'User',
    no_peer_info => 'No peer information available',
);

sub L {
    my ($key) = @_;
    my $lang_key = "tailscale $key";
    return $Lang::tr{$lang_key} || $fallback{$key} || $key;
}

sub run_service_command {
    my ($command) = @_;
    return `$sudo_cmd -n $service $command 2>&1`;
}

sub run_service_command_result {
    my ($command) = @_;
    my $output = `$sudo_cmd -n $service $command 2>&1`;
    my $rc = $? >> 8;
    return ($output, $rc);
}

sub shell_quote {
    my ($value) = @_;
    $value = '' if !defined $value;
    $value =~ s/\r//g;
    $value =~ s/\n/ /g;
    $value =~ s/'/'"'"'/g;
    return "'" . $value . "'";
}

sub checkbox_value {
    my ($name) = @_;
    return (defined $settings{$name} && $settings{$name} eq 'on') ? 'on' : 'off';
}

sub read_config {
    my %config = (
        AUTH_KEY            => '',
        HOSTNAME            => 'ipfire',
        ACCEPT_ROUTES       => 'on',
        ACCEPT_DNS          => 'off',
        ADVERTISE_EXIT_NODE => 'off',
        ADVERTISE_ROUTES    => '',
        EXTRA_ARGS          => '',
    );

    if (open(my $fh, '<', $settings_file)) {
        while (my $line = <$fh>) {
            chomp $line;
            next if $line =~ /^\s*#/ || $line =~ /^\s*$/;
            next unless $line =~ /^([A-Z_]+)=(.*)$/;

            my ($key, $value) = ($1, $2);
            next unless exists $config{$key};

            $value =~ s/^\s+|\s+$//g;
            if ($value =~ /^'(.*)'$/) {
                $value = $1;
                $value =~ s/'"'"'/'/g;
            }
            elsif ($value =~ /^"(.*)"$/) {
                $value = $1;
            }
            $config{$key} = $value;
        }
        close($fh);
    }

    for my $key (qw(ACCEPT_ROUTES ACCEPT_DNS ADVERTISE_EXIT_NODE)) {
        $config{$key} = $config{$key} eq 'on' ? 'on' : 'off';
    }

    return %config;
}

sub form_config {
    my %config = read_config();

    for my $key (qw(AUTH_KEY HOSTNAME ADVERTISE_ROUTES EXTRA_ARGS)) {
        $config{$key} = defined $settings{$key} ? $settings{$key} : '';
        $config{$key} =~ s/\r//g;
        $config{$key} =~ s/\n/ /g;
    }

    $config{'ACCEPT_ROUTES'}       = checkbox_value('ACCEPT_ROUTES');
    $config{'ACCEPT_DNS'}          = checkbox_value('ACCEPT_DNS');
    $config{'ADVERTISE_EXIT_NODE'} = checkbox_value('ADVERTISE_EXIT_NODE');

    return %config;
}

sub save_config {
    my %config = @_;
    my ($fh, $filename) = tempfile('tailscale-settings.XXXXXX', DIR => '/tmp', UNLINK => 0);

    print $fh "AUTH_KEY=" . shell_quote($config{'AUTH_KEY'}) . "\n";
    print $fh "HOSTNAME=" . shell_quote($config{'HOSTNAME'}) . "\n";
    print $fh "ACCEPT_ROUTES=$config{'ACCEPT_ROUTES'}\n";
    print $fh "ACCEPT_DNS=$config{'ACCEPT_DNS'}\n";
    print $fh "ADVERTISE_EXIT_NODE=$config{'ADVERTISE_EXIT_NODE'}\n";
    print $fh "ADVERTISE_ROUTES=" . shell_quote($config{'ADVERTISE_ROUTES'}) . "\n";
    print $fh "EXTRA_ARGS=" . shell_quote($config{'EXTRA_ARGS'}) . "\n";
    close($fh);

    my $output = run_service_command("save_settings $filename");
    unlink $filename if -f $filename;
    return $output;
}

sub set_notice {
    my ($type, $text) = @_;
    $notice_type = $type;
    $notice_text = $text;
    $show_output = 1;
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
        login_state  => L('not_logged_in'),
        advertise_routes => L('not_set'),
        exit_node        => L('no'),
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
            $info{'exit_node'} = L('yes');
        }

        if ($self->{'Online'}) {
            $info{'login_state'} = L('connected');
        }
        elsif ($self->{'ID'}) {
            $info{'login_state'} = L('logged_in');
        }
        if ($info{'exit_node'} eq L('no') && defined $status_text) {
            my $self_name = $info{'hostname'};
            for my $line (split(/\n/, $status_text)) {
                next if $line =~ /^\s*$/;
                if ($self_name ne '' && $line =~ /\b\Q$self_name\E\b/ && $line =~ /offers exit node/i) {
                    $info{'exit_node'} = L('yes');
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
            my $state = $p->{'Online'} ? L('online') : L('offline');

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
            my $state = L('online');

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

# Action handling.
if ($action eq 'start') {
    my ($output, $rc) = run_service_command_result('start');
    set_notice($rc == 0 ? 'success' : 'error', $rc == 0 ? L('service_started') : L('service_start_failed'));
}
elsif ($action eq 'stop') {
    my ($output, $rc) = run_service_command_result('stop');
    set_notice($rc == 0 ? 'success' : 'error', $rc == 0 ? L('service_stopped') : L('service_stop_failed'));
}
elsif ($action eq 'restart') {
    my ($output, $rc) = run_service_command_result('restart');
    set_notice($rc == 0 ? 'success' : 'error', $rc == 0 ? L('service_restarted') : L('service_restart_failed'));
}
elsif ($action eq 'save') {
    my %config = form_config();
    save_config(%config);
    set_notice('success', L('config_saved'));
}
elsif ($action eq 'up') {
    my %config = form_config();
    save_config(%config);

    my ($output, $rc) = run_service_command_result('up');
    set_notice($rc == 0 ? 'success' : 'error', $rc == 0 ? L('joined') : L('join_failed'));
}
elsif ($action eq 'down') {
    my ($output, $rc) = run_service_command_result('down');
    set_notice($rc == 0 ? 'success' : 'error', $rc == 0 ? L('disconnected') : L('disconnect_failed'));
}
elsif ($action eq 'resume') {
    my ($output, $rc) = run_service_command_result('up');
    set_notice($rc == 0 ? 'success' : 'error', $rc == 0 ? L('resumed') : L('resume_failed'));
}
elsif ($action eq 'logout') {
    my ($output, $rc) = run_service_command_result('logout');
    set_notice($rc == 0 ? 'success' : 'error', $rc == 0 ? L('logged_out') : L('logout_failed'));
}
elsif ($action eq 'refresh') {
    set_notice('success', L('refreshed'));
}

# Status loading.
my $service_check = run_service_command('status');
my $running = (($? >> 8) == 0 || $service_check =~ /running/i) ? 1 : 0;
my %conn = get_connection_info();
my %config = read_config();

# Page.
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
.ipfire-note.error {
    border-color: #e5b4b4;
    background: #fdeeee;
    color: #8a1f1f;
}
.config-input {
    width: 100%;
    max-width: 520px;
}
.config-help {
    color: #666;
    font-size: 11px;
}
</style>
EOF

&Header::openbigbox('100%', 'left', '', '');
print "<form method='post'>";

# Service status.
&Header::openbox('100%', 'left', L('service_status'));

print "<b>" . &Header::escape(L('status')) . ":</b> ";
if ($running) {
    print "<span class='status-dot running'></span><span style='color:green;'>" . &Header::escape(L('running')) . "</span>";
}
else {
    print "<span class='status-dot stopped'></span><span style='color:red;'>" . &Header::escape(L('stopped')) . "</span>";
}

print "<br><br>";

print "<button type='submit' name='ACTION' value='start'>" . &Header::escape(L('start')) . "</button>  ";
print "<button type='submit' name='ACTION' value='stop'>" . &Header::escape(L('stop')) . "</button>  ";
print "<button type='submit' name='ACTION' value='restart'>" . &Header::escape(L('restart')) . "</button>  ";
print "<button type='submit' name='ACTION' value='down'>" . &Header::escape(L('disconnect')) . "</button>  ";
print "<button type='submit' name='ACTION' value='resume'>" . &Header::escape(L('resume')) . "</button>  ";
print "<button type='submit' name='ACTION' value='refresh'>" . &Header::escape(L('refresh')) . "</button>  ";

if ($show_output) {
    print "<br><br>";
    print "<div class='ipfire-note " . &Header::escape($notice_type) . "'>";
    print &Header::escape($notice_text);
    print "</div>";
}

&Header::closebox();

# Runtime settings.
&Header::openbox('100%', 'left', L('runtime_config'));

my $accept_routes_checked = $config{'ACCEPT_ROUTES'} eq 'on' ? " checked='checked'" : '';
my $accept_dns_checked = $config{'ACCEPT_DNS'} eq 'on' ? " checked='checked'" : '';
my $exit_node_checked = $config{'ADVERTISE_EXIT_NODE'} eq 'on' ? " checked='checked'" : '';

print "<table class='info-table'>";
print "<tr><td class='key'>" . &Header::escape(L('auth_key')) . "</td><td><input class='config-input' type='password' name='AUTH_KEY' value='" . &Header::escape($config{'AUTH_KEY'}) . "' autocomplete='off'><div class='config-help'>" . &Header::escape(L('auth_key_help')) . "</div></td></tr>";
print "<tr><td class='key'>" . &Header::escape(L('hostname')) . "</td><td><input class='config-input' type='text' name='HOSTNAME' value='" . &Header::escape($config{'HOSTNAME'}) . "'></td></tr>";
print "<tr><td class='key'>" . &Header::escape(L('accept_routes')) . "</td><td><input type='checkbox' name='ACCEPT_ROUTES' value='on'$accept_routes_checked></td></tr>";
print "<tr><td class='key'>" . &Header::escape(L('accept_dns')) . "</td><td><input type='checkbox' name='ACCEPT_DNS' value='on'$accept_dns_checked></td></tr>";
print "<tr><td class='key'>" . &Header::escape(L('exit_node')) . "</td><td><input type='checkbox' name='ADVERTISE_EXIT_NODE' value='on'$exit_node_checked></td></tr>";
print "<tr><td class='key'>" . &Header::escape(L('advertise_routes')) . "</td><td><input class='config-input' type='text' name='ADVERTISE_ROUTES' value='" . &Header::escape($config{'ADVERTISE_ROUTES'}) . "' placeholder='192.168.101.0/24'></td></tr>";
print "<tr><td class='key'>" . &Header::escape(L('extra_args')) . "</td><td><input class='config-input' type='text' name='EXTRA_ARGS' value='" . &Header::escape($config{'EXTRA_ARGS'}) . "'></td></tr>";
print "</table>";
print "<br>";
print "<button type='submit' name='ACTION' value='save'>" . &Header::escape(L('save_config')) . "</button>  ";
print "<button type='submit' name='ACTION' value='up'>" . &Header::escape(L('join_network')) . "</button>  ";
print "<button type='submit' name='ACTION' value='logout'>" . &Header::escape(L('leave_network')) . "</button>";

&Header::closebox();

# Connection info.
&Header::openbox('100%', 'left', L('connection_info'));

print "<table class='info-table'>";
print "<tr><td class='key'>" . &Header::escape(L('hostname')) . "</td><td>" . &Header::escape($conn{'hostname'}) . "</td></tr>";
print "<tr><td class='key'>" . &Header::escape(L('assigned_address')) . "</td><td>" . &Header::escape($conn{'tailscale_ip'}) . "</td></tr>";
print "<tr><td class='key'>" . &Header::escape(L('login_state')) . "</td><td>" . &Header::escape($conn{'login_state'}) . "</td></tr>";
print "<tr><td class='key'>" . &Header::escape(L('advertise_routes')) . "</td><td>" . &Header::escape($conn{'advertise_routes'}) . "</td></tr>";
print "<tr><td class='key'>" . &Header::escape(L('exit_node')) . "</td><td>" . &Header::escape($conn{'exit_node'}) . "</td></tr>";
print "<tr><td class='key'>" . &Header::escape(L('peer_total')) . "</td><td>" . &Header::escape($conn{'peer_total'}) . "</td></tr>";
print "<tr><td class='key'>" . &Header::escape(L('peer_online')) . "</td><td>" . &Header::escape($conn{'peer_online'}) . "</td></tr>";
print "</table>";

&Header::closebox();

# Peer info.
&Header::openbox('100%', 'left', L('peer_info'));

print "<table class='peer-table'>";
print "<tr><th>" . &Header::escape(L('tailscale_ip')) . "</th><th>" . &Header::escape(L('hostname')) . "</th><th>" . &Header::escape(L('user')) . "</th><th>" . &Header::escape(L('status')) . "</th></tr>";

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
    print "<tr><td colspan='4'>" . &Header::escape(L('no_peer_info')) . "</td></tr>";
}

print "</table>";

&Header::closebox();

print "\n";
print "</form>";

&Header::closebigbox();
&Header::closepage();
