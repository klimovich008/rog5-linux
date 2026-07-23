[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$cache = Join-Path $repo 'artifacts\host-tools'
$archive = Join-Path $cache 'platform-tools_r37.0.0-win.zip'
$partial = "$archive.part"
$destination = Join-Path $cache 'google-r37.0.0'
$url = 'https://dl.google.com/android/repository/platform-tools_r37.0.0-win.zip'
$expectedSize = 8092164
$expectedSha1 = 'f29bfb58d0d6f9a57d7dbcba6cc259f9ca6f58f1'

New-Item -ItemType Directory -Force -Path $cache | Out-Null
if (Test-Path -LiteralPath $partial) {
    throw "Refusing existing partial download: $partial"
}
if (-not (Test-Path -LiteralPath $archive)) {
    curl.exe --fail --location --retry 3 --output $partial $url
    if ($LASTEXITCODE -ne 0) { throw 'Platform-Tools download failed' }
    Move-Item -LiteralPath $partial -Destination $archive
}

$file = Get-Item -LiteralPath $archive
$sha1 = (Get-FileHash -Algorithm SHA1 -LiteralPath $archive).Hash.ToLowerInvariant()
if ($file.Length -ne $expectedSize -or $sha1 -ne $expectedSha1) {
    throw 'Platform-Tools package does not match the official SDK repository metadata'
}
if (-not (Test-Path -LiteralPath $destination)) {
    Expand-Archive -LiteralPath $archive -DestinationPath $destination
}

$tools = Join-Path $destination 'platform-tools'
$adb = Join-Path $tools 'adb.exe'
$fastboot = Join-Path $tools 'fastboot.exe'
foreach ($tool in @($adb, $fastboot)) {
    if (-not (Test-Path -LiteralPath $tool)) { throw "Missing tool: $tool" }
    if ((Get-AuthenticodeSignature -LiteralPath $tool).Status -ne 'Valid') {
        throw "Invalid executable signature: $tool"
    }
}
& $adb version | Select-Object -First 2
& $fastboot --version | Select-Object -First 1
Write-Output "PASS Google Platform-Tools 37.0.0: $tools"
