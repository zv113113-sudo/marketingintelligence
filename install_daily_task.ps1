$ErrorActionPreference = "Stop"
$taskName = "Marketing Intelligence Daily"
$feedbackTaskName = "Marketing Intelligence Feedback"
$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$dailyScript = Join-Path $projectDir "daily_run.ps1"
$feedbackScript = Join-Path $projectDir "subscriber_bot.py"
$python = "C:\Users\0\AppData\Local\Programs\Python\Python313\python.exe"
$powershell = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
$logPath = Join-Path $projectDir "outputs\schedule_install.log"

function Invoke-Schtasks([string[]]$Arguments) {
    $output = & "$env:SystemRoot\System32\schtasks.exe" @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw (($output | Out-String).Trim())
    }
    return ($output | Out-String).Trim()
}

try {
    $dailyAction = '"' + $powershell + '" -NoProfile -ExecutionPolicy Bypass -File "' + $dailyScript + '"'
    $feedbackAction = '"' + $python + '" -X utf8 -u "' + $feedbackScript + '"'

    $dailyOutput = Invoke-Schtasks @(
        "/Create", "/F", "/TN", $taskName,
        "/SC", "DAILY", "/ST", "08:00", "/TR", $dailyAction,
        "/RL", "LIMITED", "/IT"
    )
    $feedbackOutput = Invoke-Schtasks @(
        "/Create", "/F", "/TN", $feedbackTaskName,
        "/SC", "ONLOGON", "/TR", $feedbackAction,
        "/RL", "LIMITED", "/IT"
    )

    $dailyDetails = Invoke-Schtasks @("/Query", "/TN", $taskName, "/FO", "LIST")
    $feedbackDetails = Invoke-Schtasks @("/Query", "/TN", $feedbackTaskName, "/FO", "LIST")
    $log = @(
        "CREATED " + (Get-Date -Format "yyyy-MM-dd HH:mm:ss"),
        $dailyOutput,
        $feedbackOutput,
        "--- daily task ---",
        $dailyDetails,
        "--- feedback task ---",
        $feedbackDetails
    )
    Set-Content -Path $logPath -Value $log -Encoding UTF8
    Write-Host "Schedule configured: daily at 08:00; feedback polling at Windows logon."
    Write-Host "Details saved to outputs\schedule_install.log."
} catch {
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $message = "FAILED " + $stamp + ": " + $_.Exception.Message
    Add-Content -Path $logPath -Value $message -Encoding UTF8
    Write-Host "Schedule setup failed: " $_.Exception.Message
    exit 1
}
