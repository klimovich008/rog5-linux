param(
    [Parameter(Mandatory)] [string] $SshKey,
    [Parameter(Mandatory)] [string] $SshHost,
    [string] $SshUser = 'root'
)

$ErrorActionPreference = 'Stop'
$SshKey = (Resolve-Path -LiteralPath $SshKey).Path
$pidFile = Join-Path (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path '.rog5-tunnel.pid'
$ports = 6080, 7681

foreach ($port in $ports) {
    $listener = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue
    if ($listener) { throw "Local port $port is already in use" }
}

$arguments = @(
    '-N', '-o', 'BatchMode=yes', '-o', 'ExitOnForwardFailure=yes',
    '-o', 'ServerAliveInterval=30', '-o', 'ServerAliveCountMax=3',
    '-o', 'StrictHostKeyChecking=accept-new', '-i', $SshKey,
    '-L', '127.0.0.1:6080:127.0.0.1:6080',
    '-L', '127.0.0.1:7681:127.0.0.1:7681',
    "$SshUser@$SshHost"
)

$process = Start-Process ssh.exe -ArgumentList $arguments -WindowStyle Hidden -PassThru
Start-Sleep -Milliseconds 700
if ($process.HasExited) { throw "SSH tunnel exited with code $($process.ExitCode)" }

Set-Content -LiteralPath $pidFile -Value $process.Id -NoNewline
Write-Output "PASS tunnel_pid=$($process.Id) noVNC=http://127.0.0.1:6080/vnc.html ttyd=http://127.0.0.1:7681/"
