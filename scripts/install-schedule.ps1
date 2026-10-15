param(
  [switch]$Install,
  [switch]$Remove,
  [string]$TaskName = "SlimAI-Competitor-News-Monitor",
  [string]$Config = "$PSScriptRoot\..\config\monitor.toml",
  [string]$Frequency = "",
  [string]$Time = "",
  [string]$Weekday = ""
)
$ErrorActionPreference = "Stop"
$root = (Resolve-Path "$PSScriptRoot\..").Path
$runner = Join-Path $root "scripts\run.ps1"
$schedule = (python (Join-Path $root "monitor.py") --config $Config schedule-info | ConvertFrom-Json)
if (-not $Frequency) { $Frequency = $schedule.frequency }
if (-not $Time) { $Time = $schedule.time }
if (-not $Weekday) { $Weekday = $schedule.weekday }

if ($Remove) {
  Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction Stop
  Write-Host "Da go lich: $TaskName"
  exit 0
}

if (-not $Install) {
  Write-Host "Che do xem truoc. Khong co thay doi he thong."
  Write-Host "Config enabled: $($schedule.enabled)"
  Write-Host "Task: $TaskName | Frequency: $Frequency | Time: $Time | Weekday: $Weekday"
  Write-Host "Chay lai voi -Install de tao lich, hoac -Remove de go."
  exit 0
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$runner`""
if ($Frequency -eq "weekly") {
  $trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $Weekday -At $Time
} else {
  $trigger = New-ScheduledTaskTrigger -Daily -At $Time
}
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description "Competitor and industry news briefing" -Force | Out-Null
Write-Host "Da tao lich: $TaskName"
