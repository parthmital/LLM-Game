$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$RootPath = $PSScriptRoot
$SetupScript = Join-Path $RootPath "scripts\setup.ps1"
$ToolingScript = Join-Path $RootPath "scripts\tooling-env.ps1"

. $ToolingScript

$Tooling = Set-RepoLocalToolingEnvironment -RootPath $RootPath
$Python = Join-Path $RootPath ".venv\Scripts\python.exe"
$NpmCommand = Get-RepoNpmCommand

& $SetupScript -RootPath $RootPath

Write-Host "Running backend syntax check..."
Invoke-RepoNativeCommand -FilePath $Python -Arguments @("-m", "compileall", (Join-Path $RootPath "Backend")) -FailureMessage "Backend syntax check failed"

Write-Host "Running backend architecture tests..."
Invoke-RepoNativeCommand -FilePath $Python -Arguments @("-m", "unittest", "discover", "-s", (Join-Path $RootPath "Backend\tests")) -FailureMessage "Backend architecture tests failed"

Write-Host "Running frontend checks..."
Push-Location (Join-Path $RootPath "Frontend")
try {
    Invoke-RepoNativeCommand -FilePath $NpmCommand -Arguments @("--cache", $Tooling.NpmCache, "run", "format:check") -FailureMessage "Frontend format check failed"
    Invoke-RepoNativeCommand -FilePath $NpmCommand -Arguments @("--cache", $Tooling.NpmCache, "run", "typecheck") -FailureMessage "Frontend typecheck failed"
    Invoke-RepoNativeCommand -FilePath $NpmCommand -Arguments @("--cache", $Tooling.NpmCache, "run", "lint") -FailureMessage "Frontend lint failed"
    Invoke-RepoNativeCommand -FilePath $NpmCommand -Arguments @("--cache", $Tooling.NpmCache, "run", "test") -FailureMessage "Frontend tests failed"
    Invoke-RepoNativeCommand -FilePath $NpmCommand -Arguments @("--cache", $Tooling.NpmCache, "run", "build") -FailureMessage "Frontend build failed"
}
finally {
    Pop-Location
}

Write-Host "All checks passed."
