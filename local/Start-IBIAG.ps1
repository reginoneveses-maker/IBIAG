param([ValidateSet("Start", "Stop")][string]$Action = "Start")
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$ConfigFolder = Join-Path $env:LOCALAPPDATA "IBIAG\Local"
$ConfigFile = Join-Path $ConfigFolder ".env.local"
$ComposeFile = Join-Path $Root "compose.local.yaml"
$AppUrl = "http://127.0.0.1:8787"
$SavedEnvironment = @{}

function Invoke-Compose {
    param([Parameter(ValueFromRemainingArguments=$true)][string[]]$Arguments)
    & docker compose --project-name ibiag-local --project-directory $Root --env-file $ConfigFile -f $ComposeFile @Arguments
    if ($LASTEXITCODE -ne 0) { throw "A operacao local nao terminou. Os dados existentes foram mantidos." }
}
function New-RandomHex {
    $bytes = New-Object byte[] 32
    $generator = [Security.Cryptography.RandomNumberGenerator]::Create()
    try { $generator.GetBytes($bytes) } finally { $generator.Dispose() }
    return ([BitConverter]::ToString($bytes)).Replace("-", "").ToLowerInvariant()
}

try {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "Instale o Docker Desktop para Windows em https://www.docker.com/products/docker-desktop/ e abra-o. Depois clique novamente em Iniciar IBIAG."
    }
    if ($env:DOCKER_HOST) { throw "DOCKER_HOST esta definido. Use um Docker Desktop local, sem conexao remota." }
    $ContextName = (& docker context show)
    if ($LASTEXITCODE -ne 0) { throw "Abra o Docker Desktop e tente novamente." }
    $ContextData = (& docker context inspect $ContextName | ConvertFrom-Json)
    if ($LASTEXITCODE -ne 0) { throw "Nao foi possivel verificar o Docker local." }
    $Endpoint = $ContextData.Endpoints.docker.Host
    if ($Endpoint -notmatch '^(npipe|unix)://') { throw "O contexto Docker aponta para outro computador. Selecione o Docker Desktop local." }
    $Engine = (& docker version --format '{{.Server.Version}}')
    if ($LASTEXITCODE -ne 0) { throw "Abra o Docker Desktop e aguarde ele iniciar." }
    if ([version](($Engine -split '-')[0]) -lt [version]"28.0.0") { throw "Atualize o Docker Desktop: este pacote exige Docker Engine 28 ou superior." }
    $OperatingSystem = (& docker info --format '{{.OSType}}')
    if ($LASTEXITCODE -ne 0 -or $OperatingSystem -ne "linux") { throw "Ative Linux containers no Docker Desktop." }
    $ComposeVersion = (& docker compose version --short).Trim().TrimStart("v")
    if ($LASTEXITCODE -ne 0 -or [version](($ComposeVersion -split '-')[0]) -lt [version]"2.24.0") {
        throw "Atualize o Docker Desktop para incluir Docker Compose 2.24 ou superior."
    }
    # Fixed local project and file: do not inherit another deployment's settings.
    foreach ($Key in @("LOCAL_MONGO_ROOT_PASSWORD", "LOCAL_DB_PASSWORD", "LOCAL_JWT_SECRET", "COMPOSE_PROFILES", "COMPOSE_ENV_FILES")) {
        $SavedEnvironment[$Key] = [Environment]::GetEnvironmentVariable($Key, "Process")
        [Environment]::SetEnvironmentVariable($Key, $null, "Process")
    }
    if (-not (Test-Path -LiteralPath $ConfigFile)) {
        if ($Action -eq "Stop") { throw "Nao existe uma instalacao local configurada para parar." }
        # Listing succeeds with empty output on first install. An inspect of a
        # missing volume emits stderr, which is terminating in Windows PS 5.1.
        $LocalVolumes = @(& docker volume ls --format '{{.Name}}')
        if ($LASTEXITCODE -ne 0) { throw "Nao foi possivel consultar os volumes locais. Nenhuma configuracao foi criada." }
        if ($LocalVolumes -contains "ibiag-local_mongo_data") {
            throw "Existem dados locais, mas a configuracao original nao foi encontrada. Nao gere outras senhas nem apague o volume; recupere a configuracao original."
        }
        New-Item -ItemType Directory -Force -Path $ConfigFolder | Out-Null
        # Restrict the secret folder before writing any credentials.
        $Sid = [Security.Principal.WindowsIdentity]::GetCurrent().User
        $Acl = New-Object Security.AccessControl.DirectorySecurity
        $Acl.SetOwner($Sid)
        $Acl.SetAccessRuleProtection($true, $false)
        $Rule = New-Object Security.AccessControl.FileSystemAccessRule($Sid, "FullControl", "ContainerInherit,ObjectInherit", "None", "Allow")
        $Acl.AddAccessRule($Rule)
        Set-Acl -LiteralPath $ConfigFolder -AclObject $Acl
        $Lines = @(
            "LOCAL_MONGO_ROOT_PASSWORD=$(New-RandomHex)",
            "LOCAL_DB_PASSWORD=$(New-RandomHex)",
            "LOCAL_JWT_SECRET=$(New-RandomHex)"
        )
        $Stream = [IO.File]::Open($ConfigFile, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
        try {
            $Bytes = [Text.Encoding]::ASCII.GetBytes(($Lines -join [Environment]::NewLine) + [Environment]::NewLine)
            $Stream.Write($Bytes, 0, $Bytes.Length)
        } finally { $Stream.Dispose() }
    }
    if ($Action -eq "Stop") {
        Invoke-Compose stop
        Write-Host "IBIAG parada. Banco e documentos locais foram preservados."
    } else {
        Write-Host "Preparando IBIAG local. A primeira abertura baixa componentes e pode demorar."
        Invoke-Compose up -d --wait --wait-timeout 180
        # Interactive first-owner setup stores only a password hash in Mongo.
        Invoke-Compose exec api python local_admin.py
        $Health = Invoke-RestMethod -Uri "$AppUrl/api/health" -TimeoutSec 15
        if ($Health.status -ne "ok" -or $Health.database -ne "ok") { throw "O banco local ainda nao esta pronto." }
        # A desktop shortcut avoids future terminal commands.
        try {
            $Desktop = [Environment]::GetFolderPath("Desktop")
            $Shell = New-Object -ComObject WScript.Shell
            $Shortcut = $Shell.CreateShortcut((Join-Path $Desktop "IBIAG.lnk"))
            $Shortcut.TargetPath = Join-Path $Root "Iniciar IBIAG.cmd"
            $Shortcut.WorkingDirectory = $Root
            $Shortcut.Description = "Abrir IBIAG no computador"
            $Shortcut.Save()
        } catch { Write-Host "Use Iniciar IBIAG.cmd nesta pasta para abrir novamente." }
        Start-Process $AppUrl
        Write-Host "IBIAG local pronta em $AppUrl"
    }
} catch {
    Write-Host ""
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
} finally {
    foreach ($Key in $SavedEnvironment.Keys) {
        [Environment]::SetEnvironmentVariable($Key, $SavedEnvironment[$Key], "Process")
    }
}
