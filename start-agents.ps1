# Start all agents script
# This script starts all three agents in separate PowerShell windows
# Order: Deposit (8001) -> Loan (8002) -> Manager (8000)

$projectPath = "c:\projects\personal_projects\cd14769-GCP-AgenticAI-C4-Classroom\project"

Write-Host "Starting Multi-Agent Banking System..." -ForegroundColor Green
Write-Host ""

# Start Deposit Agent (port 8001) - must start first
Write-Host "Starting Deposit Agent on port 8001..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectPath'; Write-Host 'DEPOSIT AGENT (Port 8001)' -ForegroundColor Cyan; adk web --port 8001 starter.deposit"

# Wait for deposit agent to initialize
Write-Host "Waiting 5 seconds for Deposit Agent to initialize..."
Start-Sleep -Seconds 5

# Start Loan Agent (port 8002) - depends on deposit for A2A
Write-Host "Starting Loan Agent on port 8002..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectPath'; Write-Host 'LOAN AGENT (Port 8002)' -ForegroundColor Cyan; adk web --port 8002 starter.loan"

# Wait for loan agent to initialize
Write-Host "Waiting 5 seconds for Loan Agent to initialize..."
Start-Sleep -Seconds 5

# Start Manager Agent (port 8000) - depends on both deposit and loan
Write-Host "Starting Manager Agent on port 8000..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectPath'; Write-Host 'MANAGER AGENT (Port 8000)' -ForegroundColor Cyan; adk web --port 8000 starter.manager"

Write-Host ""
Write-Host "All agents started!" -ForegroundColor Green
Write-Host ""
Write-Host "Access URLs:" -ForegroundColor Cyan
Write-Host "  Deposit Agent: http://localhost:8001"
Write-Host "  Loan Agent:    http://localhost:8002"
Write-Host "  Manager Agent: http://localhost:8000"
Write-Host ""
Write-Host "Note: Make sure MCP Toolbox is running first (.\start-toolbox.ps1)"
