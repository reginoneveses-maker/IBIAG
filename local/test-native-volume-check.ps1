# Regression for PS5.1 native stderr: use a real docker.cmd shim, not a function.
$ErrorActionPreference = "Stop"
$Root = Join-Path ([IO.Path]::GetTempPath()) ("ibiag-native-" + [guid]::NewGuid().ToString("N"))
$OldPath = $env:PATH
$OldAppData = $env:LOCALAPPDATA
$OldDockerHost = $env:DOCKER_HOST
$OldCase = $env:IBIAG_TEST_VOLUME_CASE
try {
    New-Item -ItemType Directory -Path (Join-Path $Root "bin") -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $Root "local") -Force | Out-Null
    Copy-Item (Join-Path $PSScriptRoot "Start-IBIAG.ps1") (Join-Path $Root "local\Start-IBIAG.ps1")
    $Stub = @'
@echo off
if "%~1 %~2"=="context show" (echo desktop-linux&exit /b 0)
if "%~1 %~2"=="context inspect" (echo [{"Endpoints":{"docker":{"Host":"npipe:////./pipe/ibiag-test"}}}]&exit /b 0)
if "%~1"=="version" (echo 28.5.1&exit /b 0)
if "%~1"=="info" (echo linux&exit /b 0)
if "%~1 %~2"=="compose version" (echo 2.40.0&exit /b 0)
if "%~1"=="compose" exit /b 0
if "%~1 %~2"=="volume ls" goto volumes
if "%~1 %~2"=="volume inspect" (echo Error response from daemon: no such volume 1>&2&exit /b 1)
echo Unexpected native Docker call 1>&2
exit /b 9
:volumes
if "%IBIAG_TEST_VOLUME_CASE%"=="Existing" echo ibiag-local_mongo_data
if "%IBIAG_TEST_VOLUME_CASE%"=="Failure" (echo Synthetic volume listing denied 1>&2&exit /b 1)
exit /b 0
'@
    [IO.File]::WriteAllText((Join-Path $Root "bin\docker.cmd"), $Stub, [Text.Encoding]::ASCII)
    $Wrapper = @'
function Invoke-RestMethod { param($Uri, $TimeoutSec); return @{status="ok"; database="ok"} }
function Start-Process { param($FilePath) }
& (Join-Path $PSScriptRoot "local\Start-IBIAG.ps1") -Action Start
exit $LASTEXITCODE
'@
    [IO.File]::WriteAllText((Join-Path $Root "run.ps1"), $Wrapper, [Text.Encoding]::ASCII)
    $env:PATH = (Join-Path $Root "bin") + ";" + $OldPath
    $env:DOCKER_HOST = $null
    foreach ($Case in @("Empty", "Existing", "Failure")) {
        $env:LOCALAPPDATA = Join-Path $Root $Case
        $env:IBIAG_TEST_VOLUME_CASE = $Case
        $Output = & powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Root "run.ps1")
        $Code = $LASTEXITCODE
        $Config = Join-Path $env:LOCALAPPDATA "IBIAG\Local\.env.local"
        if ($Case -eq "Empty") {
            if ($Code -ne 0 -or -not (Test-Path -LiteralPath $Config)) {
                throw "First install failed with native empty volume listing: $Output"
            }
        } else {
            if ($Code -eq 0 -or (Test-Path -LiteralPath $Config)) {
                throw "Unsafe configuration creation for volume state $Case"
            }
            if ($Case -eq "Existing" -and ($Output -join " ") -notmatch "Existem dados locais") {
                throw "Existing-volume guard did not produce the expected instruction"
            }
        }
        Write-Host "PASS: native Docker shim, volume state $Case"
    }
} finally {
    $env:PATH = $OldPath
    $env:LOCALAPPDATA = $OldAppData
    $env:DOCKER_HOST = $OldDockerHost
    $env:IBIAG_TEST_VOLUME_CASE = $OldCase
    if (Test-Path -LiteralPath $Root) { Remove-Item -LiteralPath $Root -Recurse -Force }
}

# Expected negative child cases leave LASTEXITCODE=1; the successful harness must exit zero.
exit 0
