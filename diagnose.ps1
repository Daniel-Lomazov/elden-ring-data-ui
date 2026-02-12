Write-Host "================================" -ForegroundColor Cyan
Write-Host "Elden Ring Data UI - Diagnostics" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

$envName = "elden_ring_ui"
$errors = @()

# Test 1: Check environment exists
Write-Host "[TEST 1/5] Checking if environment exists..." -ForegroundColor Yellow
$envExists = conda env list | Select-String $envName
if ($envExists) {
    Write-Host "✓ Environment '$envName' exists" -ForegroundColor Green
} else {
    Write-Host "✗ Environment '$envName' NOT found" -ForegroundColor Red
    $errors += "Environment not found"
}

# Test 2: Check imports
Write-Host ""
Write-Host "[TEST 2/5] Testing package imports..." -ForegroundColor Yellow

$testScript = @'
import sys
packages = ['streamlit', 'pandas', 'numpy', 'sklearn', 'plotly']
for pkg in packages:
    try:
        __import__(pkg)
        print(f"OK:{pkg}")
    except ImportError as e:
        print(f"FAIL:{pkg}:{str(e)}")
'@

conda run -n $envName python -c $testScript 2>&1 | ForEach-Object {
    $line = "$_"
    if ($line.StartsWith("OK:")) {
        $pkg = $line.Split(':')[1]
        Write-Host "  ✓ $pkg imported successfully" -ForegroundColor Green
    } elseif ($line.StartsWith("FAIL:")) {
        $parts = $line.Split(':')
        $pkg = $parts[1]
        $err = if ($parts.Count -gt 2) { $parts[2] } else { "Unknown error" }
        Write-Host "  ✗ $pkg failed: $err" -ForegroundColor Red
        $errors += "Import failed: $pkg"
    }
}

# Test 3: Check app files
Write-Host ""
Write-Host "[TEST 3/5] Checking app files..." -ForegroundColor Yellow

$requiredFiles = @("app.py", "data_loader.py", "filtering.py", "scoring.py", "ui_components.py")
foreach ($file in $requiredFiles) {
    if (Test-Path $file) {
        Write-Host "  ✓ $file exists" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $file NOT found" -ForegroundColor Red
        $errors += "Missing file: $file"
    }
}

# Test 4: Check data directory
Write-Host ""
Write-Host "[TEST 4/5] Checking data directory..." -ForegroundColor Yellow

if (Test-Path "data" -PathType Container) {
    $csvCount = (Get-ChildItem "data" -Filter "*.csv" -Recurse | Measure-Object).Count
    if ($csvCount -gt 0) {
        Write-Host "  ✓ Found $csvCount CSV files in data/" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ No CSV files found in data/" -ForegroundColor Yellow
        Write-Host "    Add CSV files to data/ and data/items/ to use the app" -ForegroundColor Cyan
    }
} else {
    Write-Host "  ✗ data/ directory NOT found" -ForegroundColor Red
    $errors += "Missing data directory"
}

# Test 5: Test app import
Write-Host ""
Write-Host "[TEST 5/5] Testing app.py import..." -ForegroundColor Yellow

conda run -n $envName python -c "import app; print('OK:app')" 2>&1 | ForEach-Object {
    $line = "$_"
    if ($line.Contains("OK:app")) {
        Write-Host "  ✓ app.py imports successfully" -ForegroundColor Green
    } else {
        Write-Host "  ✗ app.py import failed" -ForegroundColor Red
        Write-Host "    Error: $line" -ForegroundColor Red
        $errors += "app.py import failed"
    }
}

# Summary
Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
if ($errors.Count -eq 0) {
    Write-Host "✓ All diagnostics passed!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Your environment is ready. Run the app with:" -ForegroundColor White
    Write-Host "  conda run -n $envName streamlit run app.py" -ForegroundColor Cyan
} else {
    Write-Host "✗ Issues found:" -ForegroundColor Red
    foreach ($error in $errors) {
        Write-Host "  • $error" -ForegroundColor Red
    }
    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Yellow
    Write-Host "  1. Check that all CSV files are in data/ and data/items/" -ForegroundColor Cyan
    Write-Host "  2. Ensure all .py files are present in the project root" -ForegroundColor Cyan
    Write-Host "  3. Run .\setup.ps1 again to reinstall dependencies" -ForegroundColor Cyan
}
Write-Host ""