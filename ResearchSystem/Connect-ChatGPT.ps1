param([string]$TunnelId, [switch]$ReplaceKey, [switch]$SaveKeyOnly)
$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$client = Join-Path $projectRoot 'data\tunnel-client\bin\tunnel-client.exe'
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
$database = Join-Path $projectRoot 'data\real-books.sqlite3'
$models = Join-Path $projectRoot 'data\models'
$profileDirectory = Join-Path $projectRoot 'data\tunnel-client\profiles'
$healthFile = Join-Path $projectRoot 'data\tunnel-client\health.url'
. (Join-Path $projectRoot 'Tunnel-Credentials.ps1')
$credentialPath = Join-Path $projectRoot 'data\tunnel-client\runtime-key.dpapi'
$connectionPath = Join-Path $projectRoot 'data\tunnel-client\connection.json'
foreach ($required in @($client, $python, $database)) {
    if (-not (Test-Path -LiteralPath $required)) { throw "Required file missing: $required" }
}
if (-not $TunnelId -and (Test-Path -LiteralPath $connectionPath)) {
    $TunnelId = (Get-Content -LiteralPath $connectionPath -Raw | ConvertFrom-Json).tunnel_id
}
if (-not $TunnelId) { $TunnelId = Read-Host 'Tunnel ID from OpenAI Platform (tunnel_...)' }
if ($TunnelId -notmatch '^tunnel_[A-Za-z0-9_-]+$') { throw 'Invalid tunnel ID.' }
New-Item -ItemType Directory -Force -Path $profileDirectory | Out-Null
$originalKey = $env:MGCA_BOOK_TUNNEL_KEY
$keyPointer = [IntPtr]::Zero
$secureKey = $null
Push-Location -LiteralPath $projectRoot
try {
    if (-not $ReplaceKey) { $secureKey = Get-BookTunnelSecret -Path $credentialPath }
    if (-not $secureKey) {
        if ($env:MGCA_BOOK_TUNNEL_KEY -and -not $ReplaceKey) {
            $secureKey = ConvertTo-SecureString -String $env:MGCA_BOOK_TUNNEL_KEY -AsPlainText -Force
        } else {
            $secureKey = Read-Host 'Runtime API key (hidden; saved encrypted for this Windows account)' -AsSecureString
        }
        if ($secureKey.Length -eq 0) { throw 'Runtime key is required.' }
        Save-BookTunnelSecret -Secret $secureKey -Path $credentialPath
        Write-Host 'Tunnel key saved with Windows account-bound encryption.'
    } else {
        Write-Host 'Using the saved encrypted tunnel key.'
    }
    @{tunnel_id=$TunnelId} | ConvertTo-Json | Set-Content -LiteralPath $connectionPath -Encoding UTF8
    if ($SaveKeyOnly) { Write-Host 'Credential saved. Tunnel not started.'; return }
    if ($secureKey) {
        $keyPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
        $env:MGCA_BOOK_TUNNEL_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($keyPointer)
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($keyPointer)
        $keyPointer = [IntPtr]::Zero
    }
    if (-not $env:MGCA_BOOK_TUNNEL_KEY) { throw 'Runtime key is required.' }
    $env:HF_HOME = Join-Path $projectRoot 'data\hf-home'
    $env:HF_XET_CACHE = Join-Path $projectRoot 'data\hf-xet'
    $env:HF_HUB_DISABLE_XET = '1'
    $mcpCommand = '"{0}" -m book_research.cli --db "{1}" --cpu-embed --model-cache "{2}" serve' -f $python.Replace('\','/'), $database.Replace('\','/'), $models.Replace('\','/')
    Write-Host 'Starting the private book tunnel. Keep this terminal open while testing.'
    Write-Host 'In ChatGPT Plugins: + > Add custom MCP server > Connection: Tunnel.'
    Write-Host "Select $TunnelId and name it MGCA Book Research."
    Write-Host "Local health URL will be written to $healthFile"
    & $client run --profile-dir $profileDirectory `
        --control-plane.tunnel-id $TunnelId `
        --control-plane.api-key env:MGCA_BOOK_TUNNEL_KEY `
        --mcp.command "command=$mcpCommand" `
        --mcp.stdio-send-initialized-notification `
        --health.listen-addr '127.0.0.1:0' --health.url-file $healthFile
    if ($LASTEXITCODE -ne 0) { throw "Tunnel client stopped with exit code $LASTEXITCODE" }
} finally {
    if ($keyPointer -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($keyPointer) }
    $env:MGCA_BOOK_TUNNEL_KEY = $originalKey
    if ($secureKey) { $secureKey.Dispose() }
    Pop-Location
}
