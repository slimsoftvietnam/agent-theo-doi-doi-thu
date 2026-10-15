param(
  [string]$Config = "$PSScriptRoot\..\config\monitor.toml",
  [string]$RunId = ""
)
$ErrorActionPreference = "Stop"
$root = (Resolve-Path "$PSScriptRoot\..").Path
$arguments = @("$root\monitor.py", "--config", $Config, "run")
if ($RunId) { $arguments += @("--run-id", $RunId) }
python @arguments
exit $LASTEXITCODE
