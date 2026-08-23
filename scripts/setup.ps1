[CmdletBinding()]
param(
	[string]$RootPath,
	[switch]$SkipBackend,
	[switch]$SkipFrontend
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$ScriptRoot = Split-Path -Parent $PSCommandPath
if (-not $RootPath) {
	$RootPath = Join-Path $ScriptRoot ".."
}

. (Join-Path $ScriptRoot "tooling-env.ps1")

$Tooling = Set-RepoLocalToolingEnvironment -RootPath $RootPath
$RootPath = $Tooling.RootPath

if (-not $SkipBackend) {
	$VenvPath = Join-Path $RootPath ".venv"
	$VenvPython = Join-Path $VenvPath "Scripts\python.exe"

	if (-not (Test-Path -LiteralPath $VenvPython)) {
		Write-Host "Creating repository Python virtual environment at .venv..."
		$PythonCommand = Get-RepoPythonCommand
		$VenvArguments = @()
		$VenvArguments += $PythonCommand.Arguments
		$VenvArguments += @("-m", "venv", $VenvPath)
		Invoke-RepoNativeCommand -FilePath $PythonCommand.File -Arguments $VenvArguments -FailureMessage "Failed to create .venv"
	}

	if (-not (Test-Path -LiteralPath $VenvPython)) {
		throw "Python virtual environment was not created at $VenvPath."
	}

	Write-Host "Installing backend requirements into .venv..."
	$env:PIP_REQUIRE_VIRTUALENV = "true"
	Invoke-RepoNativeCommand -FilePath $VenvPython -Arguments @("-m", "pip", "install", "--upgrade", "pip", "--cache-dir", $Tooling.PipCache) -FailureMessage "Failed to upgrade pip in .venv"
	Invoke-RepoNativeCommand -FilePath $VenvPython -Arguments @("-m", "pip", "install", "--requirement", (Join-Path $RootPath "Backend\requirements.txt"), "--cache-dir", $Tooling.PipCache) -FailureMessage "Failed to install backend requirements into .venv"
}

if (-not $SkipFrontend) {
	Write-Host "Running npm install for the frontend..."
	$NpmCommand = Get-RepoNpmCommand
	Push-Location (Join-Path $RootPath "Frontend")
	try {
		Invoke-RepoNativeCommand -FilePath $NpmCommand -Arguments @("--cache", $Tooling.NpmCache, "install") -FailureMessage "Failed to run frontend npm install"
	}
	finally {
		Pop-Location
	}
}
