[CmdletBinding()]
param(
	[string]$RootPath,
	[int]$ReadyTimeoutSeconds = 300,
	[switch]$NoBrowser
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
$StopFile = Join-Path $Tooling.TempPath "dev.stop"
$ServiceScript = Join-Path $ScriptRoot "dev-service.ps1"
$PowerShellCommand = Get-RepoPowerShellCommand
$script:TerminalProcesses = @{}
$script:CleanupStarted = $false

function Remove-DevRuntimeSignals {
	Remove-Item -LiteralPath $StopFile -Force -ErrorAction SilentlyContinue
	Remove-Item -LiteralPath (Join-Path $Tooling.TempPath "dev-Backend.failed") -Force -ErrorAction SilentlyContinue
	Remove-Item -LiteralPath (Join-Path $Tooling.TempPath "dev-Frontend.failed") -Force -ErrorAction SilentlyContinue
}

function Stop-DevServiceWindows {
	if ($script:CleanupStarted) {
		return
	}

	$script:CleanupStarted = $true
	Write-Host "Stopping local services..."
	try {
		New-Item -ItemType File -Path $StopFile -Force | Out-Null
		Start-Sleep -Seconds 2

		foreach ($Entry in $script:TerminalProcesses.GetEnumerator()) {
			$ServiceName = $Entry.Key
			$TerminalProcess = Get-Process -Id $Entry.Value.Id -ErrorAction SilentlyContinue
			if (-not $TerminalProcess) {
				continue
			}

			$TerminalProcess.Refresh()
			if ($TerminalProcess.HasExited) {
				continue
			}

			$Closed = $TerminalProcess.CloseMainWindow()
			if ($Closed) {
				$TerminalProcess.WaitForExit(5000) | Out-Null
			}

			$TerminalProcess = Get-Process -Id $Entry.Value.Id -ErrorAction SilentlyContinue
			if ($TerminalProcess -and -not $TerminalProcess.HasExited) {
				Write-Host "Forcing $ServiceName terminal to close."
				Stop-RepoProcessTree -ProcessId $TerminalProcess.Id
			}
		}

		try {
			Stop-RepoPortOwner -Port 8000 -RootPath $RootPath
			Stop-RepoPortOwner -Port 8080 -RootPath $RootPath
		}
		catch {
			Write-Host $_.Exception.Message
		}
	}
	finally {
		Remove-Item -LiteralPath $StopFile -Force -ErrorAction SilentlyContinue
	}
}

function Assert-ServiceWindowsHealthy {
	foreach ($ServiceName in @("Backend", "Frontend")) {
		$FailureFile = Join-Path $Tooling.TempPath "dev-$ServiceName.failed"
		if (Test-Path -LiteralPath $FailureFile) {
			$FailureText = Get-Content -LiteralPath $FailureFile -Raw
			throw $FailureText.Trim()
		}

		if (-not $script:TerminalProcesses.ContainsKey($ServiceName)) {
			continue
		}

		$TerminalProcess = Get-Process -Id $script:TerminalProcesses[$ServiceName].Id -ErrorAction SilentlyContinue
		if (-not $TerminalProcess) {
			throw "$ServiceName terminal closed unexpectedly."
		}

		$TerminalProcess.Refresh()
		if ($TerminalProcess.HasExited) {
			throw "$ServiceName terminal exited unexpectedly."
		}
	}
}

function Test-BackendReady {
	try {
		$Response = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -TimeoutSec 2 -ErrorAction Stop
		return $Response.ready -eq $true
	}
	catch {
		return $false
	}
}

function Test-FrontendReady {
	try {
		$Response = Invoke-WebRequest -Uri "http://localhost:8080" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
		return $Response.StatusCode -ge 200 -and $Response.StatusCode -lt 500
	}
	catch {
		return $false
	}
}

function Wait-ForServicesReady {
	$StartedAt = Get-Date
	$LastStatusAt = $StartedAt.AddSeconds(-10)

	while (((Get-Date) - $StartedAt).TotalSeconds -lt $ReadyTimeoutSeconds) {
		Assert-ServiceWindowsHealthy
		$BackendReady = Test-BackendReady
		$FrontendReady = Test-FrontendReady

		if ($BackendReady -and $FrontendReady) {
			return
		}

		if (((Get-Date) - $LastStatusAt).TotalSeconds -ge 5) {
			$BackendStatus = if ($BackendReady) { "ready" } else { "waiting" }
			$FrontendStatus = if ($FrontendReady) { "ready" } else { "waiting" }
			Write-Host "Waiting for services: backend $BackendStatus, frontend $FrontendStatus."
			$LastStatusAt = Get-Date
		}

		Start-Sleep -Seconds 1
	}

	throw "Services were not ready within $ReadyTimeoutSeconds seconds."
}

trap {
	Stop-DevServiceWindows
	exit 130
}

try {
	Remove-DevRuntimeSignals

	Write-Host "Preparing repository-local development environment..."
	& (Join-Path $ScriptRoot "setup.ps1") -RootPath $RootPath

	Write-Host "Checking for stale repository services on ports 8000 and 8080..."
	Stop-RepoPortOwner -Port 8000 -RootPath $RootPath
	Stop-RepoPortOwner -Port 8080 -RootPath $RootPath

	foreach ($ServiceName in @("Backend", "Frontend")) {
		$Arguments = @(
			"-NoProfile",
			"-ExecutionPolicy",
			"Bypass",
			"-File",
			"`"$ServiceScript`"",
			"-Service",
			$ServiceName,
			"-RootPath",
			"`"$RootPath`"",
			"-StopFile",
			"`"$StopFile`""
		)

		$TerminalProcess = Start-Process -FilePath $PowerShellCommand -ArgumentList $Arguments -PassThru
		$script:TerminalProcesses[$ServiceName] = $TerminalProcess
		Write-Host "$ServiceName terminal PID: $($TerminalProcess.Id)"
	}

	Wait-ForServicesReady

	Write-Host "Backend and frontend are ready."
	if (-not $NoBrowser) {
		Write-Host "Opening http://localhost:8080..."
		Start-Process "http://localhost:8080"
	}

	Write-Host "Services are running in separate terminal windows. Press Ctrl+C here to stop everything."
	while ($true) {
		Assert-ServiceWindowsHealthy
		Start-Sleep -Seconds 1
	}
}
finally {
	Stop-DevServiceWindows
}
