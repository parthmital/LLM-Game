[CmdletBinding()]
param(
	[Parameter(Mandatory = $true)]
	[ValidateSet("Backend", "Frontend")]
	[string]$Service,
	[Parameter(Mandatory = $true)]
	[string]$RootPath,
	[Parameter(Mandatory = $true)]
	[string]$StopFile
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

. (Join-Path $PSScriptRoot "tooling-env.ps1")

$Tooling = Set-RepoLocalToolingEnvironment -RootPath $RootPath
$RootPath = $Tooling.RootPath
$FailureFile = Join-Path $Tooling.TempPath "dev-$Service.failed"
$ServiceProcess = $null

try {
	[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
	$OutputEncoding = [System.Text.Encoding]::UTF8
	$Host.UI.RawUI.WindowTitle = "LLM Game $Service"

	if ($Service -eq "Backend") {
		$WorkingDirectory = Join-Path $RootPath "Backend"
		$Command = Join-Path $RootPath ".venv\Scripts\python.exe"
		$CommandArguments = @("-u", "server.py")
	}
	else {
		$WorkingDirectory = Join-Path $RootPath "Frontend"
		$Command = Get-RepoNpmCommand
		$CommandArguments = @("run", "dev")
	}

	if (-not (Test-Path -LiteralPath $Command) -and $Service -eq "Backend") {
		throw "Backend Python was not found at $Command. Run npm run dev from the repository root to recreate setup."
	}

	Write-Host "$Service service window started."
	Write-Host "Working directory: $WorkingDirectory"
	Write-Host "Stop this window by pressing Ctrl+C in the original npm run dev terminal."

	$ServiceProcess = Start-Process -FilePath $Command -ArgumentList $CommandArguments -WorkingDirectory $WorkingDirectory -NoNewWindow -PassThru
	Write-Host "$Service process PID: $($ServiceProcess.Id)"

	while ($true) {
		$ServiceProcess.Refresh()
		if ($ServiceProcess.HasExited) {
			break
		}

		if (Test-Path -LiteralPath $StopFile) {
			Write-Host "Stop requested. Stopping $Service..."
			Stop-RepoProcessTree -ProcessId $ServiceProcess.Id
			break
		}

		Start-Sleep -Milliseconds 500
	}

	$ServiceProcess.Refresh()
	if ($ServiceProcess.HasExited) {
		$ExitCode = $ServiceProcess.ExitCode
	}
	else {
		$ExitCode = 0
	}

	if ((Test-Path -LiteralPath $StopFile) -or $ExitCode -eq 0) {
		exit $ExitCode
	}

	$FailureMessage = "$Service exited unexpectedly with code $ExitCode."
	Set-Content -LiteralPath $FailureFile -Value $FailureMessage
	Write-Host $FailureMessage
	Write-Host "Waiting for the parent dev process to clean up this window..."
	while (-not (Test-Path -LiteralPath $StopFile)) {
		Start-Sleep -Seconds 1
	}
	exit $ExitCode
}
finally {
	if ($ServiceProcess) {
		$ServiceProcess.Refresh()
		if (-not $ServiceProcess.HasExited) {
			Stop-RepoProcessTree -ProcessId $ServiceProcess.Id
		}
	}
}
