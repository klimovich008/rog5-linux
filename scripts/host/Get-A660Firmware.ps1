[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$root = Join-Path $repo 'artifacts\firmware\linux-firmware-20260622'
$base = 'https://kernel.googlesource.com/pub/scm/linux/kernel/git/firmware/linux-firmware/+/refs/tags/20260622/'
$entries = @(
    [pscustomobject]@{ Source = 'qcom/a660_sqe.fw'; Target = 'qcom/a660_sqe.fw'; Size = 43292; Sha256 = 'd222f3fe290ef0516ee0ec43082596bad2df0fcbc2e0bbb26987623cef90cf76' }
    [pscustomobject]@{ Source = 'qcom/a660_gmu.bin'; Target = 'qcom/a660_gmu.bin'; Size = 55252; Sha256 = '8acab7b417d9ebde89a1de9ae1e2c261d352fcab122e31ecd580cec9fe2ae5e7' }
    [pscustomobject]@{ Source = 'qcom/qcm6490/a660_zap.mbn'; Target = 'qcom/sm8350/a660_zap.mbn'; Size = 1054648; Sha256 = '5dbe91cb3fc9655ea2f2a9e1e169a0e30877bec84215899136a519444ca62a3d' }
)

foreach ($entry in $entries) {
    $target = Join-Path $root $entry.Target
    $partial = "$target.part"
    New-Item -ItemType Directory -Force -Path ([IO.Path]::GetDirectoryName($target)) | Out-Null
    if (Test-Path -LiteralPath $partial) { throw "Refusing existing partial file: $partial" }
    if (-not (Test-Path -LiteralPath $target)) {
        $encoded = (Invoke-WebRequest -UseBasicParsing -Uri "$base$($entry.Source)?format=TEXT").Content.Trim()
        [IO.File]::WriteAllBytes($partial, [Convert]::FromBase64String($encoded))
        Move-Item -LiteralPath $partial -Destination $target
    }
    $file = Get-Item -LiteralPath $target
    $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $target).Hash.ToLowerInvariant()
    if ($file.Length -ne $entry.Size -or $hash -ne $entry.Sha256) {
        throw "A660 firmware mismatch: $($entry.Target)"
    }
}

Write-Output "PASS pinned linux-firmware 20260622 A660 payloads: $root"
