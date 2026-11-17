# Windows-only local credential protection. No plaintext key is written to disk.
function Save-BookTunnelSecret {
    param([Parameter(Mandatory)][Security.SecureString]$Secret,
          [Parameter(Mandatory)][string]$Path)
    if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
        throw 'This credential store requires Windows DPAPI.'
    }
    $encrypted = ConvertFrom-SecureString -SecureString $Secret
    $directory = Split-Path -Parent $Path
    New-Item -ItemType Directory -Force -Path $directory | Out-Null
    $temporaryPath = $Path + '.tmp'
    try {
        Set-Content -LiteralPath $temporaryPath -Value $encrypted -Encoding ASCII -NoNewline
        Move-Item -LiteralPath $temporaryPath -Destination $Path -Force
    } finally {
        if (Test-Path -LiteralPath $temporaryPath) { Remove-Item -LiteralPath $temporaryPath }
    }
}

function Get-BookTunnelSecret {
    param([Parameter(Mandatory)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    try {
        return ConvertTo-SecureString -String (Get-Content -LiteralPath $Path -Raw).Trim()
    } catch {
        throw 'Cannot decrypt the saved tunnel key. Use the same Windows account and computer, or run Connect-ChatGPT.ps1 -ReplaceKey to save a replacement.'
    }
}
