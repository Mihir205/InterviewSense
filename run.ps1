# run.ps1 - Boot both servers
Write-Host "Starting FastAPI backend..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd c:\projects\CV\InterviewSense; .\venv\Scripts\activate; uvicorn backend.main:app --reload --port 8000"

Write-Host "Starting Next.js frontend..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd c:\projects\CV\InterviewSense\frontend; npm run dev"

Write-Host "Both servers started! Press any key to exit this launcher..." -ForegroundColor Cyan
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
