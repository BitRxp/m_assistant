param(
  [switch]$Full,
  [switch]$Dialog,
  [switch]$Bootstrap
)

$ErrorActionPreference = 'Stop'

# Start backend + OpenTTS (no web), then start Electron desktop client.
$root = (Resolve-Path (Join-Path $PSScriptRoot '..'))

$demoArgs = @()
if ($Full) { $demoArgs += '-Full' }
if ($Dialog) { $demoArgs += '-Dialog' }
if ($Bootstrap) { $demoArgs += '-Bootstrap' }
$demoArgs += @('-NoWeb')

powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root 'scripts\run_demo.ps1') @demoArgs

Write-Host "[desktop] starting electron app";
Push-Location (Join-Path $root 'apps\\desktop')
if (!(Test-Path 'node_modules')) { npm install }
# ensure web is built for packaged mode
npm run build:web
npm start
Pop-Location
