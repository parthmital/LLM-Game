function Resolve-RepoRootPath {
	param(
		[Parameter(Mandatory = $true)]
		[string]$RootPath
	)

	return (Resolve-Path -LiteralPath $RootPath).Path
}

function Set-RepoLocalToolingEnvironment {
	param(
		[Parameter(Mandatory = $true)]
		[string]$RootPath
	)

	$ResolvedRoot = Resolve-RepoRootPath -RootPath $RootPath
	$CachePath = Join-Path $ResolvedRoot ".cache"
	$NpmCache = Join-Path $CachePath "npm"
	$PipCache = Join-Path $CachePath "pip"
	$HuggingFaceCache = Join-Path $CachePath "huggingface"
	$TorchCache = Join-Path $CachePath "torch"
	$PythonCache = Join-Path $CachePath "pycache"
	$CodexLocalPath = Join-Path $ResolvedRoot ".codex-local"
	$TempPath = Join-Path $CodexLocalPath "tmp"

	@(
		$CachePath,
		$NpmCache,
		$PipCache,
		$HuggingFaceCache,
		(Join-Path $HuggingFaceCache "hub"),
		(Join-Path $HuggingFaceCache "transformers"),
		(Join-Path $HuggingFaceCache "sentence-transformers"),
		$TorchCache,
		$PythonCache,
		$CodexLocalPath,
		$TempPath
	) | ForEach-Object {
		New-Item -ItemType Directory -Force -Path $_ | Out-Null
	}

	$env:npm_config_cache = $NpmCache
	$env:PIP_CACHE_DIR = $PipCache
	$env:PIP_DISABLE_PIP_VERSION_CHECK = "1"
	$env:HF_HOME = $HuggingFaceCache
	$env:HUGGINGFACE_HUB_CACHE = Join-Path $HuggingFaceCache "hub"
	Remove-Item Env:TRANSFORMERS_CACHE -ErrorAction SilentlyContinue
	$env:SENTENCE_TRANSFORMERS_HOME = Join-Path $HuggingFaceCache "sentence-transformers"
	$env:TORCH_HOME = $TorchCache
	$env:XDG_CACHE_HOME = $CachePath
	$env:PYTHONPYCACHEPREFIX = $PythonCache
	$env:PYTHONIOENCODING = "utf-8"
	if (-not $env:NO_COLOR) {
		$env:FORCE_COLOR = "1"
	}
	$env:TQDM_DISABLE = "1"

	if (-not $env:FRONTEND_URL) {
		$env:FRONTEND_URL = "http://localhost:8080"
	}
	if (-not $env:CORS_ORIGINS) {
		$env:CORS_ORIGINS = $env:FRONTEND_URL
	}
	if (-not $env:VITE_API_URL) {
		$env:VITE_API_URL = "http://localhost:8000"
	}
	if (-not $env:VITE_DEV_HOST) {
		$env:VITE_DEV_HOST = "localhost"
	}

	return [pscustomobject]@{
		RootPath = $ResolvedRoot
		CachePath = $CachePath
		NpmCache = $NpmCache
		PipCache = $PipCache
		HuggingFaceCache = $HuggingFaceCache
		TorchCache = $TorchCache
		PythonCache = $PythonCache
		CodexLocalPath = $CodexLocalPath
		TempPath = $TempPath
	}
}

function Get-RepoPythonCommand {
	$PythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
	if (-not $PythonCommand) {
		$PythonCommand = Get-Command python -ErrorAction SilentlyContinue
	}
	if ($PythonCommand) {
		return [pscustomobject]@{
			File = $PythonCommand.Source
			Arguments = @()
		}
	}

	$PyLauncher = Get-Command py.exe -ErrorAction SilentlyContinue
	if (-not $PyLauncher) {
		$PyLauncher = Get-Command py -ErrorAction SilentlyContinue
	}
	if ($PyLauncher) {
		return [pscustomobject]@{
			File = $PyLauncher.Source
			Arguments = @("-3")
		}
	}

	throw "Python 3 is required to create the repository .venv."
}

function Get-RepoNpmCommand {
	$NpmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue
	if (-not $NpmCommand) {
		$NpmCommand = Get-Command npm -ErrorAction SilentlyContinue
	}
	if (-not $NpmCommand) {
		throw "npm is required to install frontend dependencies."
	}

	return $NpmCommand.Source
}

function Get-RepoPowerShellCommand {
	$CurrentWindowsPowerShell = Join-Path $PSHOME "powershell.exe"
	if (Test-Path -LiteralPath $CurrentWindowsPowerShell) {
		return $CurrentWindowsPowerShell
	}

	$PowerShellCommand = Get-Command powershell.exe -ErrorAction SilentlyContinue
	if ($PowerShellCommand) {
		return $PowerShellCommand.Source
	}

	$PwshCommand = Get-Command pwsh.exe -ErrorAction SilentlyContinue
	if ($PwshCommand) {
		return $PwshCommand.Source
	}

	throw "PowerShell is required to start separate service terminals."
}

function Invoke-RepoNativeCommand {
	param(
		[Parameter(Mandatory = $true)]
		[string]$FilePath,
		[string[]]$Arguments = @(),
		[string]$FailureMessage = "Command failed"
	)

	& $FilePath @Arguments
	$ExitCode = $LASTEXITCODE
	if ($null -eq $ExitCode) {
		$ExitCode = 0
	}

	if ($ExitCode -ne 0) {
		throw "$FailureMessage (exit code $ExitCode)."
	}
}

function Test-StringContainsPath {
	param(
		[string]$Value,
		[string]$Path
	)

	if ([string]::IsNullOrEmpty($Value)) {
		return $false
	}

	return $Value.IndexOf($Path, [System.StringComparison]::OrdinalIgnoreCase) -ge 0
}

function Get-RepoChildProcessIds {
	param(
		[Parameter(Mandatory = $true)]
		[int]$ParentProcessId
	)

	$Children = @(Get-CimInstance -ClassName Win32_Process -Filter "ParentProcessId = $ParentProcessId" -ErrorAction SilentlyContinue)
	foreach ($Child in $Children) {
		Get-RepoChildProcessIds -ParentProcessId ([int]$Child.ProcessId)
		[int]$Child.ProcessId
	}
}

function Stop-RepoProcessTree {
	param(
		[Parameter(Mandatory = $true)]
		[int]$ProcessId
	)

	$ProcessIds = @()
	$ProcessIds += @(Get-RepoChildProcessIds -ParentProcessId $ProcessId)
	$ProcessIds += $ProcessId
	$ProcessIds = @($ProcessIds | Select-Object -Unique)

	foreach ($Id in $ProcessIds) {
		Stop-Process -Id $Id -Force -ErrorAction SilentlyContinue
	}
}

function Test-RepoOwnedProcess {
	param(
		[Parameter(Mandatory = $true)]
		[int]$ProcessId,
		[Parameter(Mandatory = $true)]
		[string]$RootPath
	)

	$ResolvedRoot = Resolve-RepoRootPath -RootPath $RootPath
	$ProcessInfo = Get-CimInstance -ClassName Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction SilentlyContinue
	if (-not $ProcessInfo) {
		return $false
	}

	if (Test-StringContainsPath -Value ([string]$ProcessInfo.CommandLine) -Path $ResolvedRoot) {
		return $true
	}
	if (Test-StringContainsPath -Value ([string]$ProcessInfo.ExecutablePath) -Path $ResolvedRoot) {
		return $true
	}

	return $false
}

function Stop-RepoPortOwner {
	param(
		[Parameter(Mandatory = $true)]
		[int]$Port,
		[Parameter(Mandatory = $true)]
		[string]$RootPath
	)

	$Connections = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
	$OwnerIds = @($Connections | Select-Object -ExpandProperty OwningProcess -Unique | Where-Object { $_ -and $_ -ne 0 })

	foreach ($OwnerId in $OwnerIds) {
		if (Test-RepoOwnedProcess -ProcessId ([int]$OwnerId) -RootPath $RootPath) {
			Write-Host "Stopping existing repository process $OwnerId on port $Port."
			Stop-RepoProcessTree -ProcessId ([int]$OwnerId)
			continue
		}

		$OwnerProcess = Get-Process -Id $OwnerId -ErrorAction SilentlyContinue
		$OwnerName = if ($OwnerProcess) { $OwnerProcess.ProcessName } else { "unknown" }
		throw "Port $Port is already in use by PID $OwnerId ($OwnerName) outside this repository."
	}
}
