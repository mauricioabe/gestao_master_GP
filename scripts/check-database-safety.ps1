$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$migrationFiles = Get-ChildItem -Path (Join-Path $root 'backend\alembic\versions'), (Join-Path $root 'database') -Recurse -File
$pattern = '(?i)(USE\s+gestao_custos_sisfron|ALTER\s+TABLE\s+gestao_custos_sisfron|INSERT\s+INTO\s+gestao_custos_sisfron|UPDATE\s+gestao_custos_sisfron|DELETE\s+FROM\s+gestao_custos_sisfron|DROP\s+(TABLE|DATABASE).*gestao_custos_sisfron)'
$violations = $migrationFiles | Select-String -Pattern $pattern
if ($violations) {
    $violations | ForEach-Object { Write-Error $_.Line }
    exit 1
}
Write-Host 'OK: scripts de banco atuam somente no schema de projetos.' -ForegroundColor Green
