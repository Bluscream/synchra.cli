param(
    [switch]$commit,
    [switch]$push,
    [switch]$release,
    [string]$version,
    [switch]$bump,
    [switch]$publish,
    [switch]$compile,
    [switch]$build,
    [switch]$pre
)

# Configuration
$repoRoot = Split-Path -Parent $PSScriptRoot
$sdkPath = Join-Path (Split-Path -Parent $repoRoot) "synchra.py"
$pyprojectPath = Join-Path $repoRoot "pyproject.toml"

# Function to find available Python interpreters for both architectures
function Get-PythonInterpreters {
    $results = @{ x64 = $null; x86 = $null }
    $currentArch = if ([IntPtr]::Size -eq 8) { "x64" } else { "x86" }
    $results[$currentArch] = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
    
    if (-not $results.x86) {
        $x86Paths = @(
            "$env:LocalAppData\Programs\Python\Python313-32\python.exe",
            "C:\Program Files (x86)\Python314\python.exe"
        )
        foreach ($p in $x86Paths) { if (Test-Path $p) { $results.x86 = $p; break } }
    }
    
    if (-not $results.x64) {
        $x64Paths = @("C:\Program Files\Python314\python.exe", "C:\Program Files\Python313\python.exe")
        foreach ($p in $x64Paths) { if (Test-Path $p) { $results.x64 = $p; break } }
    }
    return $results
}

# Function to compile CLI into standalone binaries
function Compile-CLI {
    param([string]$arch, [string]$pythonExe)
    Write-Host "Compiling CLI for $arch using $pythonExe..." -ForegroundColor Cyan
    Push-Location $repoRoot # Dist/ must be in repo root
    try {
        & $pythonExe -m pip install --upgrade pyinstaller --user --quiet
        & $pythonExe -m pip install --no-deps "synchra.py==$targetVersion" # Skip dependency rebuilds on Python 3.14
        
        $binName = if ($arch -eq "x64") { "synchra_x64.exe" } else { "synchra_x86.exe" }
        $binDir = "dist/bin"
        if (-not (Test-Path $binDir)) { New-Item -ItemType Directory -Path $binDir -Force }
        
        # Run PyInstaller
        & $pythonExe -m PyInstaller --onefile --name $binName --clean "synchra_cli/main.py"
        
        if (Test-Path "dist/$binName") {
            Move-Item "dist/$binName" "$binDir/$binName" -Force
            Write-Host "Successfully built $binName" -ForegroundColor Green

            # Smoke Test
            Write-Host "Running smoke test for $binName..." -ForegroundColor Cyan
            $output = & "$repoRoot/$binDir/$binName" --help 2>&1 | Out-String
            if ($output -notmatch "Synchra CLI Observer") {
                Write-Error "Smoke test failed for $binName!"
                Write-Host "Output was: $output" -ForegroundColor Red
                exit 1
            }
            Write-Host "Smoke test passed for $binName." -ForegroundColor Green
        }
    } finally { Pop-Location }
}

# Version functions
function Get-CurrentVersion {
    if (Test-Path $pyprojectPath) {
        $content = Get-Content $pyprojectPath
        foreach ($line in $content) { if ($line -match '^version\s*=\s*"([^"]+)"') { return $matches[1] } }
    }
    return "0.0.0"
}
function Bump-Version {
    param($v)
    if ($v -match '^(\d+)\.(\d+)\.(\d+)$') { return "$($matches[1]).$($matches[2]).$([int]$matches[3] + 1)" }
    return $v
}
function Update-Version {
    param($newV)
    if (Test-Path $pyprojectPath) {
        $content = Get-Content $pyprojectPath
        $newContent = $content | ForEach-Object {
            if ($_ -match '^version\s*=\s*"[^"]+"') { $_ -replace 'version\s*=\s*"[^"]+"', "version = `"$newV`"" }
            elseif ($_ -match '"synchra\.py>=[^"]+"') { $_ -replace '"synchra\.py>=[^"]+"', "`"synchra.py>=$newV`"" }
            else { $_ }
        }
        $newContent | Set-Content $pyprojectPath
        Write-Host "Updated CLI version and SDK dependency to $newV"
    }
}

$doAll = -not ($commit -or $push -or $release -or $version -or $bump -or $publish -or $compile -or $pre)
$currentVersion = Get-CurrentVersion
$targetVersion = if ($bump -or $doAll) { Bump-Version $currentVersion } else { $currentVersion }
if ($version) { $targetVersion = $version }

if ($bump -or $version -or $doAll) { Update-Version $targetVersion }

if ($compile -or $build -or $doAll) {
    $interpreters = Get-PythonInterpreters
    if ($interpreters.x64) { Compile-CLI -arch "x64" -pythonExe $interpreters.x64 }
    if ($interpreters.x86) { Compile-CLI -arch "x86" -pythonExe $interpreters.x86 }
}

if ($commit -or $doAll) {
    Write-Host "Committing CLI changes..."
    Push-Location $repoRoot
    try {
        git add .
        $msg = if ($release -or $doAll) { "v${targetVersion}: Release CLI" } else { "Update to v${targetVersion}" }
        if (git status --porcelain) {
            git commit -m $msg
            if ($release -or $doAll) { git tag "v${targetVersion}" -f }
        }
    } finally { Pop-Location }
}

if ($push -or $doAll) {
    Push-Location $repoRoot
    try {
        git push origin main
        if ($release -or $doAll) { git push origin "v${targetVersion}" -f }
    } finally { Pop-Location }
}

if ($release -or $doAll) {
    Push-Location $repoRoot
    try {
        if (-not (gh release view "v${targetVersion}" 2>$null)) {
            gh release create "v${targetVersion}" --title "v${targetVersion} - CLI" --notes "CLI Release v${targetVersion}"
        }
        $bins = Get-ChildItem -Path "dist/bin" -Filter "*.exe" -ErrorAction SilentlyContinue
        if ($bins) { gh release upload "v${targetVersion}" $bins.FullName --clobber }
    } finally { Pop-Location }
}

if ($publish -or $doAll) {
    Write-Host "Publishing CLI to PyPI..."
    $env:PYPI_TOKEN = [System.Environment]::GetEnvironmentVariable("PYPI_TOKEN", "User")
    Push-Location $repoRoot
    try {
        Remove-Item -Path "dist" -Recurse -ErrorAction SilentlyContinue
        python -m build
        python -m twine upload -u "__token__" -p "$env:PYPI_TOKEN" dist/* --non-interactive --skip-existing
    } finally { Pop-Location }
}

Write-Host "CLI Build completed. Version: $targetVersion"
