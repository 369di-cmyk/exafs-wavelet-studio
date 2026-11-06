$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$compiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
New-Item -ItemType Directory -Force (Join-Path $projectRoot 'helpers') | Out-Null
& $compiler /nologo /target:winexe "/out:$projectRoot\helpers\plot_bridge.exe" "$projectRoot\plot_bridge.cs"
if ($LASTEXITCODE -ne 0) { throw 'Plot helper build failed.' }
