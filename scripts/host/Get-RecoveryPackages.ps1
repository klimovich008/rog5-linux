[CmdletBinding()]
param(
    [string]$CacheDirectory
)

$ErrorActionPreference = 'Stop'
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
if (-not $CacheDirectory) {
    $CacheDirectory = Join-Path $repoRoot 'artifacts\recovery-inputs'
}
$CacheDirectory = [IO.Path]::GetFullPath($CacheDirectory)
New-Item -ItemType Directory -Force -Path $CacheDirectory | Out-Null

$alpineImage = 'alpine:3.24@sha256:28bd5fe8b56d1bd048e5babf5b10710ebe0bae67db86916198a6eec434943f8b'
$packages = @(
    @{
        Name = 'kexec-tools-2.0.32-r2.apk'
        Url = 'https://dl-cdn.alpinelinux.org/alpine/v3.24/community/aarch64/kexec-tools-2.0.32-r2.apk'
        Hash = 'bd8b6951f862af1123972b521c355c655b7a2f40c2bf9cfe700edd590a101c94'
    },
    @{
        Name = 'xz-libs-5.8.3-r0.apk'
        Url = 'https://dl-cdn.alpinelinux.org/alpine/v3.24/main/aarch64/xz-libs-5.8.3-r0.apk'
        Hash = '76dce86852903fef7adba0285d816e5ce9ffbe9fb3ca86bbb349b97afaba1f63'
    },
    @{
        Name = 'zstd-libs-1.5.7-r2.apk'
        Url = 'https://dl-cdn.alpinelinux.org/alpine/v3.24/main/aarch64/zstd-libs-1.5.7-r2.apk'
        Hash = '2bb5136c89f5b0bbe1554c8915a3b520d5aa63ae2a51d4d821eb81698db5a818'
    },
    @{
        Name = 'libarchive-tools-3.8.7-r0.apk'
        Url = 'https://dl-cdn.alpinelinux.org/alpine/v3.24/main/aarch64/libarchive-tools-3.8.7-r0.apk'
        Hash = '033049f6d53ff0d267341087adfe142d3e4abe8d3fcec6853e2ed7c95ce2d41e'
    }
)

foreach ($package in $packages) {
    $path = Join-Path $CacheDirectory $package.Name
    if (Test-Path -LiteralPath $path) {
        $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant()
        if ($actual -ne $package.Hash) {
            throw "Refusing unexpected cached package: $($package.Name)"
        }
        continue
    }

    $partial = "$path.part"
    if (Test-Path -LiteralPath $partial) {
        throw "Partial download already exists: $partial"
    }
    & curl.exe --fail --location --retry 3 --output $partial $package.Url
    if ($LASTEXITCODE -ne 0) {
        throw "Download failed: $($package.Name)"
    }
    $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $partial).Hash.ToLowerInvariant()
    if ($actual -ne $package.Hash) {
        throw "Downloaded package hash mismatch: $($package.Name)"
    }
    Move-Item -LiteralPath $partial -Destination $path
}

& docker pull --platform linux/arm64 $alpineImage | Out-Host
if ($LASTEXITCODE -ne 0) {
    throw 'Unable to obtain pinned Alpine aarch64 image'
}

$keys = Join-Path $CacheDirectory 'aarch64-keys'
New-Item -ItemType Directory -Force -Path $keys | Out-Null
$container = (& docker create --platform linux/arm64 $alpineImage /bin/true).Trim()
if ($LASTEXITCODE -ne 0 -or -not $container) {
    throw 'Unable to create Alpine key source container'
}
try {
    & docker cp "${container}:/etc/apk/keys/." $keys | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw 'Unable to copy Alpine aarch64 signing keys'
    }
}
finally {
    & docker rm $container | Out-Null
}

$cacheMount = "type=bind,source=$CacheDirectory,target=/input,readonly"
$verify = @('run', '--rm', '--platform', 'linux/amd64', '--mount', $cacheMount,
    $alpineImage, 'apk', '--keys-dir', '/input/aarch64-keys', 'verify')
$verify += $packages | ForEach-Object { "/input/$($_.Name)" }
& docker @verify | Out-Host
if ($LASTEXITCODE -ne 0) {
    throw 'Alpine package signature verification failed'
}

foreach ($package in $packages) {
    $path = Join-Path $CacheDirectory $package.Name
    $size = (Get-Item -LiteralPath $path).Length
    Write-Output "PASS Alpine aarch64 package $($package.Name) size=$size sha256=$($package.Hash)"
}
