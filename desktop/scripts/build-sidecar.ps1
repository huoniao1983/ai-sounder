param(
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$desktop = Join-Path $root "desktop"

if (-not $SkipInstall) {
    python -m pip install --disable-pip-version-check pyinstaller
}

python -m PyInstaller `
    --noconfirm `
    --clean `
    --name aisounder-engine `
    --onefile `
    --collect-all engine `
    --add-data "$root\assets;assets" `
    --distpath "$desktop\src-tauri\binaries" `
    --workpath "$desktop\build\pyinstaller" `
    --specpath "$desktop\build" `
    "$root\engine\api_server.py"

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE"
}

$plainExe = Join-Path $desktop "src-tauri\binaries\aisounder-engine.exe"
$targetExe = Join-Path $desktop "src-tauri\binaries\aisounder-engine-x86_64-pc-windows-msvc.exe"
Copy-Item -LiteralPath $plainExe -Destination $targetExe -Force

Write-Host "Sidecar: $desktop\src-tauri\binaries\aisounder-engine.exe"
