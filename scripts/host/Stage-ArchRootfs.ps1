[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$AuthorizedKey,
    [string]$Rootfs,
    [string]$ModulesArchive,
    [string]$Output
)

$ErrorActionPreference = 'Stop'
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
if (-not $Rootfs) { $Rootfs = Join-Path $repoRoot 'artifacts\arch\ArchLinuxARM-aarch64-latest.tar.gz' }
if (-not $ModulesArchive) { $ModulesArchive = Join-Path $repoRoot 'dist\linux-7.1.4\modules.tar.gz' }
if (-not $Output) { $Output = Join-Path $repoRoot 'artifacts\arch\rog5-arch-rootfs-7.1.4.tar.gz' }
$Rootfs = (Resolve-Path -LiteralPath $Rootfs).Path
$ModulesArchive = (Resolve-Path -LiteralPath $ModulesArchive).Path
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
$keyLines = @(Get-Content -LiteralPath $AuthorizedKey | Where-Object { $_.Trim() })
if ($keyLines.Count -ne 1 -or $keyLines[0] -notmatch '^ssh-(ed25519|rsa|ecdsa-[^ ]+) ') {
    throw 'AuthorizedKey must contain exactly one OpenSSH public key'
}
if (Test-Path -LiteralPath $Output) { throw "Refusing to overwrite $Output" }

function Invoke-Docker([string[]]$Arguments) {
    & docker @Arguments
    if ($LASTEXITCODE -ne 0) { throw "docker failed with exit code $LASTEXITCODE" }
}

$repoMount = "type=bind,source=$repoRoot,target=/workspace/repo,readonly"
$modulesMount = "type=bind,source=$ModulesArchive,target=/input/modules.tar.gz,readonly"
$keyMount = "type=bind,source=$AuthorizedKey,target=/input/authorized_key,readonly"
$pacmanCacheMount = 'type=volume,source=rog5-arch-pacman-cache,target=/var/cache/pacman/pkg'
$baseTag = "rog5-arch-base:$($rootfsHash.Substring(0,12))"
$projectCommit = (& git -C $repoRoot rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Unable to read project commit' }
$dirty = @(& git -C $repoRoot status --porcelain --untracked-files=normal)
if ($LASTEXITCODE -ne 0 -or $dirty.Count) { throw 'Commit or remove repository changes before staging' }

$baseImageId = @(& docker image ls --quiet $baseTag)
if (-not $baseImageId.Count) {
    Invoke-Docker @('import', '--platform', 'linux/arm64', $Rootfs, $baseTag)
}

$entries = @(& docker run --rm --mount $modulesMount rog5-kernel-builder:ubuntu-24.04 tar -tzf /input/modules.tar.gz)
if ($LASTEXITCODE -ne 0) { throw 'Unable to inspect modules archive' }
$releases = @($entries | ForEach-Object { if ($_ -match '^lib/modules/([^/]+)/') { $Matches[1] } } | Sort-Object -Unique)
if ($releases.Count -ne 1) { throw 'Modules archive must contain exactly one kernel release' }
$kernelRelease = $releases[0]

$container = "rog5-arch-stage-$PID"
$tarPart = "$Output.tar.part"
$gzipPart = "$Output.part"
if (Test-Path -LiteralPath $tarPart) { throw "Refusing existing temporary file $tarPart" }
if (Test-Path -LiteralPath $gzipPart) { throw "Refusing existing temporary file $gzipPart" }

$succeeded = $false
try {
    Invoke-Docker @(
        'create', '--name', $container, '--platform', 'linux/arm64',
        '--mount', $repoMount, '--mount', $modulesMount, '--mount', $keyMount, '--mount', $pacmanCacheMount,
        '--env', "ROOTFS_SHA256=$rootfsHash", '--env', "MODULES_SHA256=$modulesHash",
        '--env', "TARGET_KERNEL_RELEASE=$kernelRelease", '--env', "PROJECT_COMMIT=$projectCommit",
        $baseTag, '/bin/bash', '/workspace/repo/scripts/device/stage-arch-rootfs.sh'
    )
    Invoke-Docker @('start', '--attach', $container)
    Invoke-Docker @('export', '--output', $tarPart, $container)

    $outputDirectory = [IO.Path]::GetDirectoryName($Output)
    $outputMount = "type=bind,source=$outputDirectory,target=/output"
    $tarName = [IO.Path]::GetFileName($tarPart)
    $gzipName = [IO.Path]::GetFileName($gzipPart)
    Invoke-Docker @(
        'run', '--rm', '--mount', $outputMount, 'rog5-kernel-builder:ubuntu-24.04',
        'sh', '-c', "gzip -n -c /output/$tarName > /output/$gzipName"
    )
    Move-Item -LiteralPath $gzipPart -Destination $Output
    Remove-Item -LiteralPath $tarPart

    $verifyTag = "rog5-arch-verify:$PID"
    try {
        Invoke-Docker @('import', '--platform', 'linux/arm64', $Output, $verifyTag)
        Invoke-Docker @(
            'run', '--rm', '--platform', 'linux/arm64', '--mount', $repoMount,
            '--env', "TARGET_KERNEL_RELEASE=$kernelRelease", $verifyTag,
            '/bin/bash', '/workspace/repo/scripts/device/verify-staged-arch-rootfs.sh'
        )
    }
    finally {
        if (@(& docker image ls --quiet $verifyTag).Count) {
            & docker image rm $verifyTag | Out-Null
        }
    }
    $succeeded = $true
}
finally {
    if ($succeeded -and @(& docker container ls --all --quiet --filter "name=^/$container`$").Count) {
        & docker rm --force $container | Out-Null
    }
    elseif (-not $succeeded) {
        Write-Warning "Retained failed staging container: $container"
    }
}

$file = Get-Item -LiteralPath $Output
$hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $Output).Hash.ToLowerInvariant()
Write-Output "PASS staged Arch rootfs kernel=$kernelRelease size=$($file.Length) sha256=$hash"
