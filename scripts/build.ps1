$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$pythonExe = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) { throw 'Create .venv and install requirements-dev.txt first.' }
Push-Location frontend
try {
    npm.cmd ci
    if ($LASTEXITCODE -ne 0) { throw 'npm ci failed. Use Node.js 24 LTS.' }
    npm.cmd run lint
    if ($LASTEXITCODE -ne 0) { throw 'Frontend lint failed.' }
    npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
} finally { Pop-Location }
& "$PSScriptRoot\build_helper.ps1"
& $pythonExe "$PSScriptRoot\collect_licenses.py"
if ($LASTEXITCODE -ne 0) { throw 'License collection failed.' }
& $pythonExe -m PyInstaller --noconfirm --clean --windowed --name EXAFS_Wavelet_Studio --icon app.ico --add-data 'frontend/dist;frontend/dist' --add-data 'helpers;helpers' --collect-all webview --collect-all pythonnet --collect-all clr_loader --hidden-import webview.platforms.edgechromium --exclude-module PySide6 --exclude-module PyQt5 app.py
if ($LASTEXITCODE -ne 0) { throw 'Desktop build failed.' }
& $pythonExe "$PSScriptRoot\package_release.py"
if ($LASTEXITCODE -ne 0) { throw 'Release packaging failed.' }
$compiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
& $compiler /nologo /target:winexe /r:System.Windows.Forms.dll /r:System.Drawing.dll /r:System.IO.Compression.dll /r:System.IO.Compression.FileSystem.dll /r:Microsoft.CSharp.dll "/win32icon:$projectRoot\app.ico" "/resource:$projectRoot\release\EXAFS_Wavelet_Studio_2.1.0_Windows.zip,payload.zip" "/out:$projectRoot\release\EXAFS_Wavelet_Studio_2.1.0_Setup.exe" "$projectRoot\installer.cs"
if ($LASTEXITCODE -ne 0) { throw 'Installer build failed.' }
& $pythonExe "$PSScriptRoot\check_release.py" --source "$projectRoot\release\GitHub_Source"
if ($LASTEXITCODE -ne 0) { throw 'Source release validation failed.' }
Write-Host 'Release files are in release/. Hama is not bundled.'
