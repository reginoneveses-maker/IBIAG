# Disposable Windows runner test: no Docker daemon or real installation.
$ErrorActionPreference = "Stop"
$PreviousLocalAppData = $env:LOCALAPPDATA
$PreviousDockerHost = $env:DOCKER_HOST
$TestFolder = Join-Path ([IO.Path]::GetTempPath()) ("ibiag-launcher-" + [guid]::NewGuid().ToString("N"))
$env:LOCALAPPDATA = $TestFolder
$env:DOCKER_HOST = $null
$global:OpenedUrl = ""
$global:ComposeCalls = New-Object 'System.Collections.Generic.List[string]'
function global:docker {
    $Arguments = @($args)
    $Command = $Arguments -join " "
    $global:LASTEXITCODE = 0
    if ($Command -eq "context show") { return "desktop-linux" }
    if ($Command -eq "context inspect desktop-linux") { return '[{"Endpoints":{"docker":{"Host":"npipe:////./pipe/dockerDesktopLinuxEngine"}}}]' }
    if ($Command -like "version --format*") { return "28.5.1" }
    if ($Command -like "info --format*") { return "linux" }
    if ($Command -eq "compose version --short") { return "2.40.0" }
    if ($Command -like "volume inspect*") { $global:LASTEXITCODE = 1; return }
    if ($Arguments[0] -eq "compose") {
        $global:ComposeCalls.Add($Command)
        if ($Command -notlike "*--project-name ibiag-local*") { throw "Wrong project" }
        if ($Command -notlike "*--env-file*") { throw "Missing explicit env file" }
        return
    }
    throw "Unexpected Docker operation in launcher test"
}
function global:Invoke-RestMethod {
    param($Uri, $TimeoutSec)
    if ($Uri -ne "http://127.0.0.1:8787/api/health") { throw "Wrong health target" }
    return @{status="ok"; database="ok"}
}
function global:Start-Process {
    param($FilePath)
    $global:OpenedUrl = $FilePath
}
try {
    & (Join-Path $PSScriptRoot "Start-IBIAG.ps1") -Action Start
    $Config = Join-Path $TestFolder "IBIAG\Local\.env.local"
    $First = [IO.File]::ReadAllText($Config)
    $Lines = @(Get-Content -LiteralPath $Config)
    if ($Lines.Count -ne 3) { throw "Unexpected secret count" }
    foreach ($Line in $Lines) {
        if ($Line -notmatch '^LOCAL_(MONGO_ROOT_PASSWORD|DB_PASSWORD|JWT_SECRET)=[a-f0-9]{64}$') {
            throw "Invalid generated secret"
        }
    }
    if (-not (Get-Acl -LiteralPath (Split-Path $Config)).AreAccessRulesProtected) {
        throw "Secret folder inherited ACLs"
    }
    if ($global:OpenedUrl -ne "http://127.0.0.1:8787") { throw "Browser target not local" }
    & (Join-Path $PSScriptRoot "Start-IBIAG.ps1") -Action Stop
    & (Join-Path $PSScriptRoot "Start-IBIAG.ps1") -Action Start
    if ([IO.File]::ReadAllText($Config) -ne $First) { throw "Subsequent start rotated credentials" }
    if (($global:ComposeCalls | Where-Object { $_ -match '(^| )down( |$)|(^| )-v( |$)' }).Count) {
        throw "Launcher requested destructive removal"
    }
    Write-Host "PASS: Windows launcher first start, protected secrets, stop/start and credential preservation (Docker mocked)."
} finally {
    $env:LOCALAPPDATA = $PreviousLocalAppData
    $env:DOCKER_HOST = $PreviousDockerHost
    if (Test-Path -LiteralPath $TestFolder) { Remove-Item -LiteralPath $TestFolder -Recurse -Force }
    Remove-Item Function:\docker, Function:\Invoke-RestMethod, Function:\Start-Process -ErrorAction SilentlyContinue
}
