param(
    [switch]$DockerDown
)

$ErrorActionPreference = "Stop"

function Write-Step([string]$msg) {
    Write-Host "[demo] $msg"
}

$root = (Resolve-Path (Join-Path $PSScriptRoot ".."))
$stateDir = Join-Path $root ".demo"
$pidsPath = Join-Path $stateDir "pids.json"

if (Test-Path $pidsPath) {
    $pids = Get-Content -Raw -Path $pidsPath | ConvertFrom-Json

    foreach ($name in @("web", "backend")) {
        if ($pids.$name) {
            $pid = [int]$pids.$name
            try {
                Write-Step "stopping $name (pid=$pid)"
                Stop-Process -Id $pid -Force -ErrorAction Stop
            } catch {
                Write-Step "$name already stopped (pid=$pid)"
            }
        }
    }

    Remove-Item -Force $pidsPath
} else {
    Write-Step "no pid file found at .demo/pids.json"
}

if ($DockerDown) {
    Write-Step "docker compose down (infra/docker)"
    Push-Location (Join-Path $root "infra\\docker")
    docker compose down
    Pop-Location
}

Write-Step "done"
