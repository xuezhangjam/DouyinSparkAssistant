param([switch]$SkipInstall, [switch]$SkipArchive)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

function Invoke-Checked {
    param([string]$Program, [string[]]$Arguments)
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Program failed with exit code $LASTEXITCODE" }
}

$python = Join-Path $PSScriptRoot '.venv-win\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    Invoke-Checked 'python' @('-m', 'venv', '.venv-win')
}
if (-not $SkipInstall) {
    Invoke-Checked $python @('-m', 'pip', 'install', '-r', 'requirements-windows.txt')
}
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $PSScriptRoot '.windows-browsers'
Invoke-Checked $python @('-m', 'playwright', 'install', 'chromium')
Invoke-Checked $python @('-m', 'unittest', 'discover', '-s', 'tests', '-v')
$oldPath = $env:PATH
try {
    # Do not collect unrelated ICU/runtime DLLs from tools injected into PATH.
    # Qt uses the Windows system ICU; e.g. Poppler's same-named DLL is incompatible.
    $env:PATH = "$(Split-Path $python);$env:SystemRoot\System32;$env:SystemRoot"
    Invoke-Checked $python @('-m', 'PyInstaller', '--clean', '--noconfirm', 'SparkAssistant.spec')
} finally {
    $env:PATH = $oldPath
}
$bundle = Join-Path $PSScriptRoot 'dist\SparkAssistant-Windows-x64'
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'WINDOWS.md') -Destination (Join-Path $bundle '使用说明.md')
# Run the actual packaged worker against a temporary, empty profile.
$oldData = $env:SPARK_DATA_DIR
try {
    $env:SPARK_DATA_DIR = Join-Path $PSScriptRoot 'test-output\packaged-check'
    Invoke-Checked (Join-Path $bundle 'SparkWorker.exe') @('check')
    $env:SPARK_SMOKE_REPORT = Join-Path $env:SPARK_DATA_DIR ("gui-" + [guid]::NewGuid().ToString() + '.json')
    $guiCheck = Start-Process -FilePath (Join-Path $bundle 'SparkAssistant.exe') -WindowStyle Hidden -PassThru
    if (-not $guiCheck.WaitForExit(20000)) {
        $guiCheck.Kill()
        throw 'Packaged GUI failed to start or finish its smoke test within 20 seconds.'
    }
    if (-not (Test-Path -LiteralPath $env:SPARK_SMOKE_REPORT)) {
        throw 'Packaged GUI did not produce a startup report.'
    }
    $report = Get-Content -LiteralPath $env:SPARK_SMOKE_REPORT -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($report.status -ne 'ok') { throw 'Packaged GUI smoke test failed.' }
    Write-Host 'Packaged GUI startup: OK'
} finally {
    $env:SPARK_DATA_DIR = $oldData
    Remove-Item Env:\SPARK_SMOKE_REPORT -ErrorAction SilentlyContinue
}
if (-not $SkipArchive) {
    Invoke-Checked $python @('package_windows.py')
}
Write-Host "Windows build ready: $bundle"
