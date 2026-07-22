$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$pidFile = Join-Path $repo '.rog5-tunnel.pid'

if (-not (Test-Path -LiteralPath $pidFile)) {
    Write-Output 'Tunnel is not recorded as running'
    exit 0
}

$tunnelPid = [int](Get-Content -LiteralPath $pidFile -Raw)
$process = Get-CimInstance Win32_Process -Filter "ProcessId = $tunnelPid"
if ($process -and ($process.Name -ne 'ssh.exe' -or $process.CommandLine -notlike '*127.0.0.1:6080:127.0.0.1:6080*')) {
    throw "PID $tunnelPid is not the recorded ROG5 SSH tunnel"
}
if ($process) { Stop-Process -Id $tunnelPid }
Remove-Item -LiteralPath $pidFile
Write-Output 'PASS tunnel stopped'
