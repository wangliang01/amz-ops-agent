$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "Missing .venv. Run: uv venv .venv --python 3.11; uv pip install --python .venv\Scripts\python.exe -r requirements.txt"
}

$seed = Join-Path $root "data\seed\skus.json"
if (-not (Test-Path $seed)) {
    & $python (Join-Path $root "data\generate_seed.py")
}

Start-Process -FilePath $python `
    -ArgumentList "-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", "8000" `
    -WorkingDirectory $root

Start-Sleep -Seconds 2

Start-Process -FilePath $python `
    -ArgumentList "-m", "streamlit", "run", "app\streamlit_app.py", "--server.port", "8501" `
    -WorkingDirectory $root

Write-Host "API docs: http://127.0.0.1:8000/docs"
Write-Host "Demo UI:  http://127.0.0.1:8501"
