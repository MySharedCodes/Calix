$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$executable = "$projectRoot\src-tauri\target\release\calix.exe"
$records = @()
foreach ($mode in @('normal', 'forced', 'early')) {
    $watch = [System.Diagnostics.Stopwatch]::StartNew()
    $proc = Start-Process -FilePath $executable -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru
    $deadline = (Get-Date).AddSeconds(30)
    do {
        $proc.Refresh()
        if ($proc.MainWindowHandle -ne 0) { break }
        Start-Sleep -Milliseconds 25
    } while ((Get-Date) -lt $deadline -and -not $proc.HasExited)
    $windowMs = [Math]::Round($watch.Elapsed.TotalMilliseconds, 2)
    $backend = $null
    while ((Get-Date) -lt $deadline) {
        $backend = Get-CimInstance Win32_Process -Filter "name='calix-service.exe'" | Where-Object ParentProcessId -eq $proc.Id | Select-Object -First 1
        if ($backend) { break }
        if ($proc.HasExited) { throw "Desktop exited before starting its backend ($mode)" }
        Start-Sleep -Milliseconds 150
    }
    if (-not $backend) { Stop-Process -Id $proc.Id -ErrorAction SilentlyContinue; throw 'Backend did not start' }
    if ($mode -ne 'early') { Start-Sleep -Milliseconds 1500 }
    if ($mode -ne 'forced') {
        if (-not $proc.CloseMainWindow()) { Stop-Process -Id $proc.Id; throw 'No desktop window to close' }
        if (-not $proc.WaitForExit(15000)) { Stop-Process -Id $proc.Id; throw 'Desktop did not exit normally' }
    } else { Stop-Process -Id $proc.Id }
    $deadline = (Get-Date).AddSeconds(5)
    do {
        $remaining = Get-Process -Id $backend.ProcessId -ErrorAction SilentlyContinue
        if (-not $remaining) { break }
        Start-Sleep -Milliseconds 100
    } while ((Get-Date) -lt $deadline)
    if ($remaining) { Stop-Process -Id $backend.ProcessId -ErrorAction SilentlyContinue; throw "Backend survived $mode desktop shutdown" }
    $records += [PSCustomObject]@{ mode=$mode; status='passed'; backend_removed=$true; window_created_ms=$windowMs }
}
$records | ConvertTo-Json | Set-Content -LiteralPath "$projectRoot\work\lifecycle-report.json" -Encoding utf8
$records | Format-Table
