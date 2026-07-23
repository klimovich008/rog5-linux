[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$AuthorizedKey,
    [string]$Rootfs,
    [string]$ModulesArchive,
    [string]$FirmwareDirectory,
    [string]$Output
)

$ErrorActionPreference = 'Stop'
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
if (-not $Rootfs) { $Rootfs = Join-Path $repoRoot 'artifacts\arch\ArchLinuxARM-aarch64-latest.tar.gz' }
if (-not $ModulesArchive) { $ModulesArchive = Join-Path $repoRoot 'dist\linux-7.1.4\modules.tar.gz' }
if (-not $FirmwareDirectory) { $FirmwareDirectory = Join-Path $repoRoot 'artifacts\firmware\linux-firmware-20260622' }
if (-not $Output) { $Output = Join-Path $repoRoot 'artifacts\arch\rog5-arch-rootfs-7.1.4.tar.gz' }
$Rootfs = (Resolve-Path -LiteralPath $Rootfs).Path
$ModulesArchive = (Resolve-Path -LiteralPath $ModulesArchive).Path
$FirmwareDirectory = (Resolve-Path -LiteralPath $FirmwareDirectory).Path
$AuthorizedKey = (Resolve-Path -LiteralPath $AuthorizedKey).Path
$Output = [IO.Path]::GetFullPath($Output)
New-Item -ItemType Directory -Force -Path ([IO.Path]::GetDirectoryName($Output)) | Out-Null

$manifest = Import-Csv -Delimiter "`t" -LiteralPath (Join-Path $repoRoot 'manifests\artifacts.tsv')
function Get-VerifiedArtifact([string]$ManifestName, [string]$Path) {
    $entry = $manifest | Where-Object name -eq $ManifestName
    if (-not $entry) { throw "Missing manifest entry: $ManifestName" }
    $file = Get-Item -LiteralPath $Path
    $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
    if ($file.Length -ne [int64]$entry.size -or $hash -ne $entry.sha256) {
        throw "Artifact mismatch: $ManifestName"
    }
    return $hash
}

$rootfsHash = Get-VerifiedArtifact 'artifacts/arch/ArchLinuxARM-aarch64-latest.tar.gz' $Rootfs
$modulesHash = Get-VerifiedArtifact 'dist/linux-7.1.4/modules.tar.gz' $ModulesArchive
foreach ($relative in @('qcom/a660_sqe.fw', 'qcom/a660_gmu.bin', 'qcom/sm8350/a660_zap.mbn')) {
    Get-VerifiedArtifact "artifacts/firmware/linux-firmware-20260622/$relative" `
        (Join-Path $FirmwareDirectory $relative) | Out-Null
}
$keyLines = @(Get-Content -LiteralPath $AuthorizedKey | Where-Object { $_.Trim() })
if ($keyLines.Count -ne 1 -or $keyLines[0] -notmatch '^ssh-(ed25519|rsa|ecdsa-[^ ]+) ') {
    throw 'AuthorizedKey must contain exactly one OpenSSH public key'
}
if (Test-Path -LiteralPath $Output) { throw "Refusing to overwrite $Output" }

function Invoke-Docker([string[]]$Arguments) {
    & docker @Arguments
    if ($LASTEXITCODE -ne 0) { throw "docker failed with exit code $LASTEXITCODE" }
}

$repoMount = "type=bind,source=$repoRoot,target=/stage/workspace/repo,readonly"
$modulesMount = "type=bind,source=$ModulesArchive,target=/stage/input/modules.tar.gz,readonly"
$firmwareMount = "type=bind,source=$FirmwareDirectory,target=/stage/input/firmware,readonly"
$keyMount = "type=bind,source=$AuthorizedKey,target=/stage/input/authorized_key,readonly"
$pacmanCacheMount = 'type=volume,source=rog5-arch-pacman-cache,target=/stage/var/cache/pacman/pkg'
$rootfsMount = "type=volume,source=rog5-arch-rootfs-$PID,target=/stage"
$verifyMount = "type=volume,source=rog5-arch-verify-$PID,target=/stage"
$baseTag = "rog5-arch-base:$($rootfsHash.Substring(0,12))"
$projectCommit = (& git -C $repoRoot rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Unable to read project commit' }
$dirty = @(& git -C $repoRoot status --porcelain --untracked-files=normal)
if ($LASTEXITCODE -ne 0 -or $dirty.Count) { throw 'Commit or remove repository changes before staging' }

$baseImageId = @(& docker image ls --quiet $baseTag)
if (-not $baseImageId.Count) {
    Invoke-Docker @('import', '--platform', 'linux/arm64', $Rootfs, $baseTag)
}

$modulesFileMount = "type=bind,source=$ModulesArchive,target=/input/modules.tar.gz,readonly"
$entries = @(& docker run --rm --mount $modulesFileMount rog5-kernel-builder:ubuntu-24.04 tar -tzf /input/modules.tar.gz)
if ($LASTEXITCODE -ne 0) { throw 'Unable to inspect modules archive' }
$releases = @($entries | ForEach-Object { if ($_ -match '^lib/modules/([^/]+)/') { $Matches[1] } } | Sort-Object -Unique)
if ($releases.Count -ne 1) { throw 'Modules archive must contain exactly one kernel release' }
$kernelRelease = $releases[0]

$tarPart = "$Output.tar.part"
$gzipPart = "$Output.part"
if (Test-Path -LiteralPath $tarPart) { throw "Refusing existing temporary file $tarPart" }
if (Test-Path -LiteralPath $gzipPart) { throw "Refusing existing temporary file $gzipPart" }
$outputDirectory = [IO.Path]::GetDirectoryName($Output)
$outputMount = "type=bind,source=$outputDirectory,target=/output"
$rootfsFileMount = "type=bind,source=$Rootfs,target=/input/rootfs.tar.gz,readonly"
$tarName = [IO.Path]::GetFileName($tarPart)
$gzipName = [IO.Path]::GetFileName($gzipPart)
$succeeded = $false

try {
    Invoke-Docker @('volume', 'create', "rog5-arch-rootfs-$PID")
    Invoke-Docker @('volume', 'create', "rog5-arch-verify-$PID")
    Invoke-Docker @(
        'run', '--rm', '--mount', $rootfsMount, '--mount', $rootfsFileMount,
        'rog5-kernel-builder:ubuntu-24.04', 'bsdtar', '--acls', '--xattrs', '--fflags',
        '-xpf', '/input/rootfs.tar.gz', '-C', '/stage'
    )
    Invoke-Docker @(
        'run', '--rm', '--platform', 'linux/arm64',
        '--mount', $rootfsMount, '--mount', $repoMount, '--mount', $modulesMount, '--mount', $firmwareMount,
        '--mount', $keyMount, '--mount', $pacmanCacheMount,
        '--mount', 'type=bind,source=/dev,target=/stage/dev',
        '--mount', 'type=bind,source=/proc,target=/stage/proc',
        '--mount', 'type=bind,source=/sys,target=/stage/sys', '--tmpfs', '/stage/run',
        '--env', "ROOTFS_SHA256=$rootfsHash", '--env', "MODULES_SHA256=$modulesHash",
        '--env', "TARGET_KERNEL_RELEASE=$kernelRelease", '--env', "PROJECT_COMMIT=$projectCommit",
        $baseTag, '/bin/bash', '/stage/workspace/repo/scripts/device/run-arch-rootfs-stage.sh'
    )
    Invoke-Docker @(
        'run', '--rm', '--mount', $rootfsMount, '--mount', $outputMount,
        'rog5-kernel-builder:ubuntu-24.04', 'bsdtar', '--acls', '--xattrs', '--fflags',
        '-cpf', "/output/$tarName", '-C', '/stage',
        '--exclude', './workspace', '--exclude', './input',
        '--exclude', './dev/*', '--exclude', './proc/*', '--exclude', './sys/*', '--exclude', './run/*', '.'
    )
    Invoke-Docker @(
        'run', '--rm', '--mount', $outputMount, 'rog5-kernel-builder:ubuntu-24.04',
        'sh', '-c', "gzip -n -c /output/$tarName > /output/$gzipName"
    )
    Remove-Item -LiteralPath $tarPart

    $outputFileMount = "type=bind,source=$gzipPart,target=/input/rootfs.tar.gz,readonly"
    Invoke-Docker @(
        'run', '--rm', '--mount', $verifyMount, '--mount', $outputFileMount,
        'rog5-kernel-builder:ubuntu-24.04', 'bsdtar', '--acls', '--xattrs', '--fflags',
        '-xpf', '/input/rootfs.tar.gz', '-C', '/stage'
    )
    Invoke-Docker @(
        'run', '--rm', '--platform', 'linux/arm64', '--mount', $verifyMount, '--mount', $repoMount,
        '--mount', 'type=bind,source=/dev,target=/stage/dev',
        '--mount', 'type=bind,source=/proc,target=/stage/proc',
        '--mount', 'type=bind,source=/sys,target=/stage/sys', '--tmpfs', '/stage/run',
        '--env', "TARGET_KERNEL_RELEASE=$kernelRelease", $baseTag,
        'chroot', '/stage', '/bin/bash', '/workspace/repo/scripts/device/verify-staged-arch-rootfs.sh'
    )
    Move-Item -LiteralPath $gzipPart -Destination $Output
    $succeeded = $true
}
finally {
    if ($succeeded) {
        & docker volume rm "rog5-arch-rootfs-$PID" "rog5-arch-verify-$PID" | Out-Null
    }
    else {
        Write-Warning "Retained failed staging volumes: rog5-arch-rootfs-$PID, rog5-arch-verify-$PID"
    }
}

$file = Get-Item -LiteralPath $Output
$hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $Output).Hash.ToLowerInvariant()
Write-Output "PASS staged Arch rootfs kernel=$kernelRelease size=$($file.Length) sha256=$hash"
