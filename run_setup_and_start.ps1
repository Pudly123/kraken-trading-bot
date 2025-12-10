<#
run_setup_and_start.ps1

Creates missing helper files, updates .gitignore, stages and commits changes,
installs Python dependencies (using the python/py launcher), and starts Streamlit
on port 8050. Intended to be run from the repository root in PowerShell.

Usage (PowerShell):
  Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force
  .\run_setup_and_start.ps1

If you prefer to run only parts of it, open the script and run sections manually.
#>

param(
    [int]$Port = 8050,
    [string]$CommitMessage = "Fix Streamlit UI, add local run config and headless test"
)

function Write-Info($m) { Write-Host "[INFO] $m" -ForegroundColor Cyan }
function Write-ErrorAndExit($m) { Write-Host "[ERROR] $m" -ForegroundColor Red; exit 1 }

# 1) Ensure .streamlit/config.toml
if (-not (Test-Path -Path ".streamlit")) {
    Write-Info "Creating .streamlit directory"
    New-Item -ItemType Directory -Path .streamlit | Out-Null
}

$configPath = ".streamlit\config.toml"
$configContent = @"[server]
headless = true
port = 8050
enableCORS = false
"@
if (-not (Test-Path -Path $configPath)) {
    Write-Info "Creating $configPath"
    $configContent | Out-File -FilePath $configPath -Encoding UTF8
} else {
    Write-Info "$configPath already exists"
}

# 2) run_local.sh (for Git Bash / WSL)
$bashScript = @"#!/usr/bin/env bash
# Run the Streamlit app locally on port 8050
set -euo pipefail

PORT=${1:-8050}

echo "Starting Streamlit app on port $PORT..."
python -m streamlit run main.py --server.port "$PORT" --server.headless true
"@

if (-not (Test-Path -Path "run_local.sh")) {
    Write-Info "Creating run_local.sh"
    $bashScript | Out-File -FilePath run_local.sh -Encoding UTF8
    # make it executable in WSL/Git Bash manually if needed
} else {
    Write-Info "run_local.sh already exists"
}

# 3) run_local.ps1 (PowerShell wrapper)
$psScript = @"param([int]`$Port=8050)
Write-Host "Starting Streamlit on port `$Port..."
python -m streamlit run main.py --server.port `$Port --server.headless true
"@

if (-not (Test-Path -Path "run_local.ps1")) {
    Write-Info "Creating run_local.ps1"
    $psScript | Out-File -FilePath run_local.ps1 -Encoding UTF8
} else {
    Write-Info "run_local.ps1 already exists"
}

# 4) run_headless_test.py
$headless = @"import numpy as np
from trading_logic import TradingStrategy
from kraken_api import KrakenAPI

def generate_price_series(base=50000, n=500, volatility=0.002):
    prices = [base]
    for _ in range(n-1):
        change = prices[-1] * volatility * (np.random.random() - 0.5)
        prices.append(prices[-1] + change)
    return prices

def main():
    print("Starting headless test...")
    try:
        api = KrakenAPI()
        print("KrakenAPI instantiated.")
    except Exception as e:
        print(f"KrakenAPI import/instantiation failed: {e}")

    strategy = TradingStrategy()
    prices = generate_price_series()
    result = strategy.simulate_strategy(
        historical_prices=prices,
        initial_balance=10000,
        rsi_period=14,
        oversold=30,
        overbought=70,
        stop_loss=2.0,
        take_profit=4.0,
        position_size_pct=10
    )

    print("Simulation results:")
    print(f" Final balance: ${result['final_balance']:,.2f}")
    print(f" Total trades: {result['total_trades']}")
    print(f" Winning trades: {result['winning_trades']}")
    print(f" Win rate: {result['win_rate']:.2f}%")
    print(f" Total profit: ${result['total_profit']:,.2f}")

    if result['trades']:
        print(" First 5 trades:")
        for t in result['trades'][:5]:
            print(t)

if __name__ == '__main__':
    main()
"@

if (-not (Test-Path -Path "run_headless_test.py")) {
    Write-Info "Creating run_headless_test.py"
    $headless | Out-File -FilePath run_headless_test.py -Encoding UTF8
} else {
    Write-Info "run_headless_test.py already exists"
}

# 5) .gitignore
$gitignoreContent = @".local/
.replit
fix-streamlit.patch
"@
if (-not (Test-Path -Path ".gitignore")) {
    Write-Info "Creating .gitignore"
    $gitignoreContent | Out-File -FilePath .gitignore -Encoding UTF8
} else {
    Write-Info ".gitignore already exists (not overwriting)"
}

# 6) Ensure requirements.txt exists (do not overwrite if present)
if (-not (Test-Path -Path "requirements.txt")) {
    Write-Info "Creating minimal requirements.txt"
    @"streamlit>=1.28.0
plotly>=5.17.0
pandas>=2.0.0
numpy>=1.24.0
python-dotenv>=1.0.0
krakenex>=2.1.0
websocket-client>=1.6.0
pyyaml>=6.0
ta>=0.10.0
ccxt>=4.0.0
"@ | Out-File -FilePath requirements.txt -Encoding UTF8
} else {
    Write-Info "requirements.txt already exists"
}

# 7) Stage files for git
Write-Info "Staging files for git"
& git add .

# Show status
Write-Info "Git status (porcelain):"
& git status --porcelain

# 8) Commit if there are staged changes
$changes = & git status --porcelain
if ($changes) {
    Write-Info "Committing changes"
    & git commit -m $CommitMessage
    if ($LASTEXITCODE -ne 0) { Write-ErrorAndExit "git commit failed (exit $LASTEXITCODE)" }
    Write-Info "Pushing to origin main"
    & git push origin main
    if ($LASTEXITCODE -ne 0) { Write-Info "Push failed; try creating a branch and pushing it manually." }
} else {
    Write-Info "No changes to commit"
}

# 9) Ensure Python available
$pythonCmd = $null
if (Get-Command py -ErrorAction SilentlyContinue) { $pythonCmd = 'py -3' }
elseif (Get-Command python -ErrorAction SilentlyContinue) { $pythonCmd = 'python' }
else { Write-ErrorAndExit "Python not found. Install Python 3 and re-run this script." }

# 10) Install dependencies
Write-Info "Installing Python dependencies using $pythonCmd"
& $pythonCmd -m pip install --upgrade pip
& $pythonCmd -m pip install -r requirements.txt

# 11) Start Streamlit (foreground)
Write-Info "Starting Streamlit on port $Port (use Ctrl+C to stop)"
& $pythonCmd -m streamlit run main.py --server.port $Port --server.headless true

Write-Info "Script finished"
