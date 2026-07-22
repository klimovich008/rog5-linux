param(
    [Parameter(Mandatory)] [string] $KernelSource,
    [string] $Fragment = (Join-Path $PSScriptRoot '..\..\configs\kernel\rog5-mainline.fragment')
)

$ErrorActionPreference = 'Stop'
$KernelSource = (Resolve-Path -LiteralPath $KernelSource).Path
$Fragment = (Resolve-Path -LiteralPath $Fragment).Path

$known = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
if (Test-Path -LiteralPath (Join-Path $KernelSource '.git')) {
    $definitions = & git -C $KernelSource grep -h -E `
        '^[[:space:]]*(menu)?config[[:space:]]+[A-Z0-9_]+[[:space:]]*$' `
        HEAD -- ':(glob)**/Kconfig*'
    if ($LASTEXITCODE -ne 0) { throw 'Could not scan kernel Kconfig files with git' }
    foreach ($line in $definitions) {
        if ($line -match '^\s*(?:menu)?config\s+([A-Z0-9_]+)\s*$') {
            [void] $known.Add($Matches[1])
        }
    }
} else {
    Get-ChildItem -LiteralPath $KernelSource -Recurse -File -Filter 'Kconfig*' | ForEach-Object {
        foreach ($line in Get-Content -LiteralPath $_.FullName) {
            if ($line -match '^\s*(?:menu)?config\s+([A-Z0-9_]+)\s*$') {
                [void] $known.Add($Matches[1])
            }
        }
    }
}

$requested = foreach ($line in Get-Content -LiteralPath $Fragment) {
    if ($line -match '^(?:# )?CONFIG_([A-Z0-9_]+)(?:=| is not set)') { $Matches[1] }
}

$missing = @($requested | Where-Object { -not $known.Contains($_) } | Sort-Object -Unique)
if ($missing.Count) {
    $missing | ForEach-Object { Write-Error "Unknown kernel symbol: CONFIG_$_" }
    exit 1
}

Write-Output "PASS $($requested.Count) configuration symbols exist in $KernelSource"
