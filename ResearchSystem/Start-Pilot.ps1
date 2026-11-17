param(
    [string]$PythonExe = "$PSScriptRoot\.venv\Scripts\python.exe",
    [int]$Port = 8765,
    [switch]$CpuEmbeddings
)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $PythonExe)) {
    throw 'Python environment missing. Create .venv and install this project, or pass -PythonExe.'
}
Push-Location -LiteralPath $PSScriptRoot
try {
    $env:HF_HOME = Join-Path $PSScriptRoot 'data\hf-home'
    $env:HF_XET_CACHE = Join-Path $PSScriptRoot 'data\hf-xet'
    $env:HF_HUB_DISABLE_XET = '1'
    $taskArguments = @('-m','book_research.cli','--db','data/pilot.sqlite3')
    if ($CpuEmbeddings) { $taskArguments += '--cpu-embed' }
    & $PythonExe @taskArguments import samples
    if ($LASTEXITCODE -ne 0) { throw 'Sample import failed; server not started.' }
    Write-Host "Local search: http://127.0.0.1:$Port/library"
    & $PythonExe @taskArguments serve --transport streamable-http --port $Port
} finally {
    Pop-Location
}
