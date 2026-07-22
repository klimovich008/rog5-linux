param(
    [Parameter(Mandatory)] [string] $BootImage,
    [Parameter(Mandatory)] [string] $SshKey,
    [string] $ExpectedKernel,
    [string] $Fastboot = 'fastboot.exe',
    [string] $Serial,
    [Parameter(Mandatory)] [string] $SshHost,
    [string] $SshUser = 'root',
    [int] $TimeoutSeconds = 360,
    [switch] $SkipBoot
)

$ErrorActionPreference = 'Stop'
$BootImage = (Resolve-Path -LiteralPath $BootImage).Path
$SshKey = (Resolve-Path -LiteralPath $SshKey).Path

function Invoke-Ssh([string] $Command, [int] $ConnectTimeout = 8) {
    $args = @(
        '-o', 'BatchMode=yes', '-o', "ConnectTimeout=$ConnectTimeout",
        '-o', 'StrictHostKeyChecking=accept-new', '-i', $SshKey,
        "$SshUser@$SshHost", $Command
    )
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $output = & ssh.exe @args 2>$null
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousPreference
    }
    [pscustomobject]@{ ExitCode = $exitCode; Output = $output }
}

function Wait-Until([scriptblock] $Condition, [string] $Description) {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (& $Condition) { return }
        Start-Sleep -Seconds 2
    }
    throw "Timed out waiting for $Description"
}

$fastbootArgs = @()
if ($Serial) { $fastbootArgs += @('-s', $Serial) }

if (-not $SkipBoot) {
    $devices = & $Fastboot @fastbootArgs devices
    if (-not $devices) {
        $reboot = Invoke-Ssh 'sync; python3 /root/rog5-reboot-bootloader.py' 5
        Wait-Until { (& $Fastboot @fastbootArgs devices 2>$null) } 'fastboot device'
    }

    & $Fastboot @fastbootArgs boot $BootImage
    if ($LASTEXITCODE -ne 0) { throw 'Temporary fastboot boot failed' }
}

Wait-Until { (Invoke-Ssh 'true' 5).ExitCode -eq 0 } 'SSH'

$remoteSmoke = '/tmp/rog5-smoke-test.sh'
$localSmoke = (Resolve-Path (Join-Path $PSScriptRoot '..\device\smoke-test.sh')).Path
& scp.exe -q -o BatchMode=yes -o StrictHostKeyChecking=accept-new -i $SshKey `
    $localSmoke "${SshUser}@${SshHost}:$remoteSmoke"
if ($LASTEXITCODE -ne 0) { throw 'Could not copy smoke test' }

if ($ExpectedKernel.Contains("'")) {
    throw 'ExpectedKernel cannot contain a single quote'
}
$result = Invoke-Ssh "chmod 700 $remoteSmoke; EXPECTED_KERNEL='$ExpectedKernel' $remoteSmoke" 30
$result.Output
if ($result.ExitCode -ne 0) { throw 'Device smoke test failed' }

Write-Output 'PASS temporary boot test'
