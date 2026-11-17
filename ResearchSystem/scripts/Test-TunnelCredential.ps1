$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\Tunnel-Credentials.ps1')
$testPath = Join-Path $PSScriptRoot '..\reports\credential-test.dpapi'
$clearTest = 'test-only-' + [Guid]::NewGuid().ToString('N')
$secret = ConvertTo-SecureString -String $clearTest -AsPlainText -Force
$pointer = [IntPtr]::Zero
$recovered = $null
try {
    Save-BookTunnelSecret -Secret $secret -Path $testPath
    if ((Get-Content -LiteralPath $testPath -Raw).Contains($clearTest)) { throw 'Plaintext found in credential file.' }
    $recovered = Get-BookTunnelSecret -Path $testPath
    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($recovered)
    if ([Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer) -ne $clearTest) { throw 'Credential round-trip failed.' }
    Write-Host 'PASS: encrypted Windows DPAPI round-trip; plaintext absent from file.'
} finally {
    if ($pointer -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer) }
    $secret.Dispose()
    if ($recovered) { $recovered.Dispose() }
    if (Test-Path -LiteralPath $testPath) { Remove-Item -LiteralPath $testPath }
}
