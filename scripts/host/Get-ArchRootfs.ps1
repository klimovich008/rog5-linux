[CmdletBinding()]
param(
    [string]$RootfsUrl = 'https://ca.us.mirror.archlinuxarm.org/os/ArchLinuxARM-aarch64-latest.tar.gz',
    [string]$KeyringRepository = 'https://github.com/archlinuxarm/archlinuxarm-keyring.git',
    [string]$KeyringCommit = '91e6b11698f8df66042d56aaa56fbe9c9263847d',
    [string]$CacheDirectory
)

$ErrorActionPreference = 'Stop'
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
if (-not $CacheDirectory) {
    $CacheDirectory = Join-Path $repoRoot 'artifacts\arch'
}
$CacheDirectory = [IO.Path]::GetFullPath($CacheDirectory)
New-Item -ItemType Directory -Force -Path $CacheDirectory | Out-Null

$name = [IO.Path]::GetFileName(([Uri]$RootfsUrl).AbsolutePath)
if ($name -ne 'ArchLinuxARM-aarch64-latest.tar.gz') {
    throw "Refusing unexpected rootfs filename: $name"
}
$rootfs = Join-Path $CacheDirectory $name
$signature = "$rootfs.sig"
$rootfsPart = "$rootfs.part"
$signaturePart = "$signature.part"
$keyringDirectory = Join-Path $CacheDirectory "keyring-$KeyringCommit"

function Invoke-Checked([string]$Command, [string[]]$Arguments) {
    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Command failed with exit code $LASTEXITCODE"
    }
}

if (-not (Test-Path (Join-Path $keyringDirectory '.git'))) {
    Invoke-Checked git @('clone', '--filter=blob:none', $KeyringRepository, $keyringDirectory)
}
$actualCommit = (& git -C $keyringDirectory rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $actualCommit -ne $KeyringCommit) {
    throw "Keyring cache is not pinned commit $KeyringCommit"
}

$cacheMount = "type=bind,source=$CacheDirectory,target=/input,readonly"
$repoMount = "type=bind,source=$repoRoot,target=/workspace/repo,readonly"
$keyring = "/input/keyring-$KeyringCommit/archlinuxarm.gpg"

function Test-Rootfs([string]$RootfsPath, [string]$SignaturePath) {
    & docker run --rm --mount $cacheMount --mount $repoMount `
        rog5-kernel-builder:ubuntu-24.04 sh /workspace/repo/scripts/device/verify-arch-rootfs.sh `
        "/input/$([IO.Path]::GetFileName($RootfsPath))" `
        "/input/$([IO.Path]::GetFileName($SignaturePath))" $keyring | Out-Host
    return $LASTEXITCODE -eq 0
}

$verified = (Test-Path -LiteralPath $rootfs) -and
    (Test-Path -LiteralPath $signature) -and
    (Test-Rootfs $rootfs $signature)
if (-not $verified) {
    if ((Test-Path -LiteralPath $rootfsPart) -and (Test-Path -LiteralPath $rootfs)) {
        throw 'Both final and partial rootfs files exist; preserve one and remove the other before retrying'
    }
    if (Test-Path -LiteralPath $rootfs) {
        Move-Item -LiteralPath $rootfs -Destination $rootfsPart
    }
    Invoke-Checked curl.exe @('--fail', '--location', '--retry', '3', '--continue-at', '-', '--output', $rootfsPart, $RootfsUrl)
    Invoke-Checked curl.exe @('--fail', '--location', '--retry', '3', '--output', $signaturePart, "$RootfsUrl.sig")
    if (-not (Test-Rootfs $rootfsPart $signaturePart)) {
        throw 'Downloaded Arch rootfs failed authentication'
    }
    Move-Item -Force -LiteralPath $rootfsPart -Destination $rootfs
    Move-Item -Force -LiteralPath $signaturePart -Destination $signature
}

$file = Get-Item -LiteralPath $rootfs
$hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $rootfs).Hash.ToLowerInvariant()
Write-Output "PASS Arch rootfs size=$($file.Length) sha256=$hash"
