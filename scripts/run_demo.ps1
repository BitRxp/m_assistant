param(
    [string]$BackendHost = "127.0.0.1",
    [int]$BackendPort = 8000,
    [string]$WebHost = "127.0.0.1",
    [int]$WebPort = 5173,
    [switch]$Full,
    [switch]$Dialog,
    [switch]$OpenBrowser,
    [switch]$NoDocker,
    [switch]$NoWeb,
    [switch]$NoBackend,
    [switch]$Bootstrap
)

$ErrorActionPreference = "Stop"

function Write-Step([string]$msg) {
    Write-Host "[demo] $msg"
}

$root = (Resolve-Path (Join-Path $PSScriptRoot ".."))
$stateDir = Join-Path $root ".demo"
$pidsPath = Join-Path $stateDir "pids.json"

if (!$OpenBrowser.IsPresent) {
    $OpenBrowser = $true
}

New-Item -ItemType Directory -Force -Path $stateDir | Out-Null

function Import-DotEnv([string]$path) {
    if (!(Test-Path $path)) { return }

    Write-Step "loading env from $path"
    $lines = Get-Content -Path $path -ErrorAction SilentlyContinue
    foreach ($line in $lines) {
        $t = $line.Trim()
        if ($t.Length -eq 0) { continue }
        if ($t.StartsWith("#")) { continue }

        if ($t -match "^([A-Za-z_][A-Za-z0-9_]*)=(.*)$") {
            $k = $matches[1]
            $v = $matches[2]

            # strip surrounding quotes
                if ($v.StartsWith('"') -and $v.EndsWith('"') -and $v.Length -ge 2) { $v = $v.Substring(1, $v.Length-2) }
                if ($v.StartsWith("'") -and $v.EndsWith("'") -and $v.Length -ge 2) { $v = $v.Substring(1, $v.Length-2) }

            # don't overwrite explicitly provided environment
            if (-not (Test-Path Env:$k)) {
                Set-Item -Path Env:$k -Value $v
            }
        }
    }
}

function Save-Pids($obj) {
    $obj | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 -Path $pidsPath
}

function Load-Pids() {
    if (!(Test-Path $pidsPath)) { return $null }
    try { return (Get-Content -Raw -Path $pidsPath | ConvertFrom-Json) } catch { return $null }
}

if ($Bootstrap) {
    Write-Step "bootstrap backend venv + deps"
    Push-Location (Join-Path $root "apps\\backend")
    if (!(Test-Path ".venv")) {
        python -m venv .venv
    }
    & .\\.venv\Scripts\Activate.ps1
    python -m pip install -U pip
    if ($Full) {
        python -m pip install -e ".[dev,stt]"
    } else {
        python -m pip install -e ".[dev]"
    }
    Pop-Location

    if (!$NoWeb) {
        Write-Step "bootstrap web deps (npm install)"
        Push-Location (Join-Path $root "apps\\web")
        if (!(Test-Path "node_modules")) {
            npm install
        }
        Pop-Location
    }
}

$pids = [ordered]@{}

# Import .env from repo root for full demo settings / secrets
Import-DotEnv (Join-Path $root ".env")

if (!$NoDocker -and !$NoBackend) {
    Write-Step "starting OpenTTS via docker compose (infra/docker)"
    Push-Location (Join-Path $root "infra\\docker")
    docker compose up -d
    Pop-Location
}

if (!$NoBackend) {
    Write-Step "starting backend on http://${BackendHost}:${BackendPort}"
    $backendDir = Join-Path $root "apps\\backend"

    # Defaults for PoC
    $env:WAKE_ENABLED = "false"
    $env:STT_BACKEND = "stub"
    if ($NoDocker) {
        $env:TTS_BACKEND = "stub"
    } else {
        $env:TTS_BACKEND = "opentts"
    }
    $env:DIALOG_ENABLED = "false"
    $env:LLM_BACKEND = "stub"

    if ($Full) {
        Write-Step "full mode: dialog + faster-whisper + Grok"
        $env:STT_BACKEND = "faster-whisper"
        $env:DIALOG_ENABLED = "true"
        $env:LLM_BACKEND = "proxy"
        $env:LLM_PRIMARY_PROVIDER = "grok"
        $env:LLM_SECONDARY_PROVIDER = "grok"
        $env:LLM_ROUTING_MODE = "priority"

        if (!(Test-Path Env:GROK_API_KEY) -or [string]::IsNullOrWhiteSpace($env:GROK_API_KEY)) {
            throw "GROK_API_KEY is required for -Full mode. Put it into .env (repo root) or export it in the shell."
        }
    } elseif ($Dialog) {
        Write-Step "dialog mode: stub STT + stub LLM"
        $env:DIALOG_ENABLED = "true"
        $env:LLM_BACKEND = "stub"
    }

    $env:BACKEND_HOST = $BackendHost
    $env:BACKEND_PORT = "$BackendPort"

    $backendArgs = @(
        "-NoProfile",
        "-Command",
        "cd `"$root`"; " +
        "if (Test-Path `"$backendDir\\.venv\\Scripts\\Activate.ps1`") { . `"$backendDir\\.venv\\Scripts\\Activate.ps1`" }; " +
        "python -m uvicorn m_assistant_backend.main:app --host $BackendHost --port $BackendPort"
    )

    $proc = Start-Process -FilePath "powershell.exe" -ArgumentList $backendArgs -PassThru
    $pids.backend = $proc.Id

    Start-Sleep -Seconds 1
}

if (!$NoWeb) {
    Write-Step "starting web dev server on http://${WebHost}:${WebPort}"
    $webDir = Join-Path $root "apps\\web"

    $webArgs = @(
        "-NoProfile",
        "-Command",
        "cd `"$webDir`"; " +
        "if (!(Test-Path node_modules)) { npm install }; " +
        "npm run dev -- --host $WebHost --port $WebPort"
    )

    $proc = Start-Process -FilePath "powershell.exe" -ArgumentList $webArgs -PassThru
    $pids.web = $proc.Id
}

Save-Pids $pids

Write-Host ""
Write-Step "done"
if (!$NoBackend) {
    Write-Host "  backend: http://${BackendHost}:${BackendPort} (/health, /metrics)"
    Write-Host "  ws:      ws://${BackendHost}:${BackendPort}/ws"
}
if (!$NoWeb) {
    Write-Host "  web:     http://${WebHost}:${WebPort}"
}
if (!$NoDocker -and !$NoBackend) {
    Write-Host "  opentts: http://localhost:5500"
}
Write-Host ""
Write-Host "To stop everything: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\stop_demo.ps1"

if ($OpenBrowser -and !$NoWeb) {
    try {
        Start-Process "http://${WebHost}:${WebPort}"
    } catch {
        # ignore
    }
}
