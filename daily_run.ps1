$ErrorActionPreference = "Stop"
$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = "C:\Users\0\AppData\Local\Programs\Python\Python313\python.exe"
$logName = "daily_run_{0}.log" -f (Get-Date -Format "yyyy-MM-dd")
$logPath = Join-Path (Join-Path $projectDir "outputs") $logName
Set-Location $projectDir
"`r`n===== Started $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz') =====" | Add-Content -Path $logPath -Encoding UTF8
& $python -X utf8 -u (Join-Path $projectDir "run.py") *>> $logPath
$exitCode = $LASTEXITCODE
"===== Finished $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz'); exit=$exitCode =====" | Add-Content -Path $logPath -Encoding UTF8
exit $exitCode
