# bootstrap.ps1
# Windows bootstrap for Django project:
# - validates structure (manage.py, settings, migrations)
# - creates venv (.venv)
# - installs requirements
# - runs Django checks + migrate (creates DB for SQLite)
# - starts runserver and opens browser

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Fail($msg) {
  Write-Host ""
  Write-Host "ERROR: $msg" -ForegroundColor Red
  Write-Host ""
  exit 1
}

function Warn($msg) {
  Write-Host "WARN:  $msg" -ForegroundColor Yellow
}

# Resolve project root = folder where this script is located
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

Write-Host "Project root: $ProjectRoot"
Write-Host ""

# --- Structure checks ---
$ManagePy = Join-Path $ProjectRoot "manage.py"
if (-not (Test-Path $ManagePy)) {
  Fail "manage.py nerastas. Įdėk bootstrap.ps1 į projekto šaknį (ten, kur manage.py) ir paleisk iš ten."
}

# A light sanity check: typical project package folder exists (your project is named 'registras')
$SettingsPy = Join-Path $ProjectRoot "registras\settings.py"
if (-not (Test-Path $SettingsPy)) {
  Warn "registras\settings.py nerastas. Jei tavo projekto paketo pavadinimas ne 'registras' – tai normalu. Jei vis dėlto 'registras', patikrink ZIP struktūrą."
}

$ReqTxt = Join-Path $ProjectRoot "requirements.txt"
if (-not (Test-Path $ReqTxt)) {
  Fail "requirements.txt nerastas. Įdėk requirements.txt į projekto šaknį."
}

# --- Migrations presence check (critical for migrate) ---
# We look for any migrations/__init__.py under immediate app folders.
$migrationInits = Get-ChildItem -Path $ProjectRoot -Filter "__init__.py" -Recurse -ErrorAction SilentlyContinue |
  Where-Object { $_.FullName -match "\\migrations\\__init__\.py$" }

if (-not $migrationInits -or $migrationInits.Count -lt 1) {
  Fail "Nerasta nei vieno migrations\__init__.py. Be migracijų komanda 'migrate' nesukurs DB. Į ZIP privalai įdėti app'ų katalogus su migrations/ (pvz. pozicijos\migrations\*)."
} else {
  Write-Host ("Migrations found: {0} app(s)" -f $migrationInits.Count)
}

# --- Media checks (optional but helpful) ---
$MediaDir = Join-Path $ProjectRoot "media"
if (-not (Test-Path $MediaDir)) {
  Warn "media/ katalogo nėra. Jei testuotojui reikia brėžinių/šriftų – įdėk media/ šalia manage.py."
} else {
  $FontReg = Join-Path $MediaDir "fonts\NotoSans-Regular.ttf"
  $FontBold = Join-Path $MediaDir "fonts\NotoSans-Bold.ttf"
  if (-not (Test-Path $FontReg)) { Warn "Trūksta media\fonts\NotoSans-Regular.ttf (PDF LT raidėms gali būti problema)." }
  if (-not (Test-Path $FontBold)) { Warn "Trūksta media\fonts\NotoSans-Bold.ttf (PDF LT raidėms gali būti problema)." }
}

# --- Python detection ---
$PythonCmd = $null
try {
  $null = Get-Command py -ErrorAction Stop
  $PythonCmd = "py"
} catch {
  try {
    $null = Get-Command python -ErrorAction Stop
    $PythonCmd = "python"
  } catch {
    Fail "Nerastas nei 'py', nei 'python'. Įdiek Python (Windows) ir pažymėk 'Add Python to PATH'."
  }
}

Write-Host "Python cmd: $PythonCmd"
Write-Host ""

# Ensure UTF-8 in this PowerShell session (helps LT chars in console)
$env:PYTHONUTF8 = "1"

# --- Venv paths ---
$VenvDir = Join-Path $ProjectRoot ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$VenvPip = Join-Path $VenvDir "Scripts\pip.exe"

# Create venv if missing
if (-not (Test-Path $VenvPython)) {
  Write-Host "Creating venv: $VenvDir"
  if ($PythonCmd -eq "py") {
    # If you need a specific version, e.g.: py -3.13 -m venv .venv
    & py -m venv $VenvDir
  } else {
    & python -m venv $VenvDir
  }
}

if (-not (Test-Path $VenvPython)) {
  Fail "Nepavyko sukurti venv (.venv). Patikrink Python diegimą."
}

# Upgrade pip
Write-Host "Upgrading pip..."
& $VenvPython -m pip install --upgrade pip

# Install deps
Write-Host "Installing requirements..."
try {
  & $VenvPip install -r $ReqTxt
} catch {
  Write-Host ""
  Warn "Nepavyko suinstaliuoti priklausomybių iš requirements.txt."
  Warn "Dažniausia priežastis Windows'e: vienam iš paketų reikia kompiliavimo įrankių."
  Warn "Jei log'e matai C/C++ build klaidas, įdiek 'Build Tools for Visual Studio' (C++ build tools) arba naudok Python versiją/paketus su paruoštais wheels."
  Write-Host ""
  throw
}

# Django checks
Write-Host "Running Django checks..."
& $VenvPython $ManagePy check

# Migrate (creates DB if SQLite and DB file missing)
Write-Host "Applying migrations (this creates DB if SQLite and DB file is missing)..."
& $VenvPython $ManagePy migrate

# SQLite typical file path note
$DbFile = Join-Path $ProjectRoot "db.sqlite3"
if (Test-Path $DbFile) {
  Write-Host "SQLite DB ready: $DbFile"
} else {
  Write-Host "Note: db.sqlite3 nerastas projekto šaknyje. Jei naudojate ne SQLite arba DB kelias kitas – tai normalu."
}

Write-Host ""
Write-Host "Starting server: http://127.0.0.1:8000/"
Write-Host "Stop server with Ctrl+C"
Write-Host ""

# Open browser (best-effort)
try { Start-Process "http://127.0.0.1:8000/" } catch {}

# Run server
& $VenvPython $ManagePy runserver 127.0.0.1:8000
