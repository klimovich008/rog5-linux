$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$pidFile = Join-Path $repo '.rog5-tunnel.pid'

if (-not (Test-Path -LiteralPath $pidFile)) {
    Write-Output 'Tunnel is not recorded as running'
    exit 0
}

$tunnelPid = [int](Get-Content -LiteralPath $pidFile -Raw)
try {
    $process = Get-Process -Id $tunnelPid -ErrorAction Stop
}
catch {
    Remove-Item -LiteralPath $pidFile
    Write-Output 'Removed stale tunnel record'
    exit 0
}

if ($process.ProcessName -ne 'ssh') { throw "PID $tunnelPid is not an SSH process" }
$requiredPorts = 6080, 7681, 9222, 13389
$ownedPorts = @(
    foreach ($port in $requiredPorts) {
        Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue |
            Where-Object OwningProcess -eq $tunnelPid |
            Select-Object -ExpandProperty LocalPort
    }
)
$missingPorts = @($requiredPorts | Where-Object { $_ -notin $ownedPorts })
if ($missingPorts.Count) {
    throw "PID $tunnelPid does not own every recorded ROG5 tunnel port"
}

Stop-Process -Id $tunnelPid
Remove-Item -LiteralPath $pidFile
Write-Output 'PASS tunnel stopped'
