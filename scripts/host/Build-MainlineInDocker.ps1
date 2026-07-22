[CmdletBinding()]
param(
    [ValidateRange(1, 256)]
    [int]$Jobs = [Math]::Max(1, [Environment]::ProcessorCount - 1),
    [string]$SourceVolume = 'rog5-linux-source-7.1.4',
    [string]$BuildVolume = 'rog5-linux-build-7.1.4',
    [string]$DistDirectory
)

$ErrorActionPreference = 'Stop'
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
if (-not $DistDirectory) {
    $DistDirectory = Join-Path $repoRoot 'dist\linux-7.1.4'
}
$DistDirectory = [IO.Path]::GetFullPath($DistDirectory)
$image = 'rog5-kernel-builder:ubuntu-24.04'

function Invoke-Docker([string[]]$Arguments) {
    & docker @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "docker command failed with exit code $LASTEXITCODE"
    }
}

Invoke-Docker @('info')
Invoke-Docker @('build', '--file', (Join-Path $repoRoot 'containers\kernel-builder\Dockerfile'), '--tag', $image, $repoRoot)
Invoke-Docker @('volume', 'create', $SourceVolume)
Invoke-Docker @('volume', 'create', $BuildVolume)

$repoMount = "type=bind,source=$repoRoot,target=/workspace/repo,readonly"
$sourceMount = "type=volume,source=$SourceVolume,target=/root/src"
$buildMount = "type=volume,source=$BuildVolume,target=/root/build"

Invoke-Docker @(
    'run', '--rm', '--mount', $repoMount, '--mount', $sourceMount, $image,
    '/workspace/repo/scripts/device/prepare-mainline.sh', '/root/src/linux-7.1.4'
)
Invoke-Docker @(
    'run', '--rm', '--mount', $repoMount, '--mount', $sourceMount, '--mount', $buildMount,
    '--env', "JOBS=$Jobs", '--env', 'FRAGMENT=/workspace/repo/configs/kernel/rog5-mainline.fragment',
    $image, '/workspace/repo/scripts/device/build-mainline.sh'
)
Invoke-Docker @(
    'run', '--rm', '--mount', $repoMount, '--mount', $buildMount, $image,
    '/workspace/repo/scripts/device/verify-mainline-build.sh'
)

New-Item -ItemType Directory -Force -Path $DistDirectory | Out-Null
$distMount = "type=bind,source=$DistDirectory,target=/dist"
$copy = @'
set -eu
src=/root/build/rog5-linux-7.1.4
install -m 0644 "$src/.config" /dist/kernel.config
install -m 0644 "$src/arch/arm64/boot/Image.gz" "$src/build-meta.txt" /dist/
install -m 0644 "$src"/arch/arm64/boot/dts/qcom/sm8350-*.dtb /dist/
'@
Invoke-Docker @('run', '--rm', '--mount', $buildMount, '--mount', $distMount, $image, 'sh', '-c', $copy)

Write-Host "PASS cross-compiled Linux 7.1.4 artifacts: $DistDirectory"
