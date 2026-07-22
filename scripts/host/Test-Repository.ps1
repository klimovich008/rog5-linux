param(
    [string] $ArtifactRoot
)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$manifest = Import-Csv -Delimiter "`t" -LiteralPath (Join-Path $repo 'manifests\artifacts.tsv')

$forbidden = rg -n -i --glob '!host/Test-Repository.ps1' `
    '(fastboot\s+flash|BEGIN (RSA|OPENSSH|EC) PRIVATE KEY|OPENROUTER_API_KEY\s*=|password\s*=)' `
    (Join-Path $repo 'scripts')
if ($LASTEXITCODE -eq 0) {
    $forbidden
    throw 'Forbidden secret or persistent-flash pattern found'
}

if ($ArtifactRoot) {
    $ArtifactRoot = (Resolve-Path -LiteralPath $ArtifactRoot).Path
    foreach ($item in $manifest) {
        $path = Join-Path $ArtifactRoot $item.name
        if (-not (Test-Path -LiteralPath $path)) {
            Write-Warning "Missing optional local artifact: $($item.name)"
            continue
        }
        $file = Get-Item -LiteralPath $path
        $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant()
        if ($file.Length -ne [int64] $item.size -or $hash -ne $item.sha256) {
            throw "Artifact mismatch: $($item.name)"
        }
        Write-Output "PASS artifact $($item.name)"
    }
}

Write-Output 'PASS repository policy checks'
