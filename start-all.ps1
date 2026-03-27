# Start everything - Toolbox and all Agents
# All agents run on the same server with A2A enabled

$projectPath = "c:\projects\personal_projects\cd14769-GCP-AgenticAI-C4-Classroom\project"
$starterPath = "c:\projects\personal_projects\cd14769-GCP-AgenticAI-C4-Classroom\project\starter"

Write-Host "========================================" -ForegroundColor Green
Write-Host "  Multi-Agent Banking System Startup" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Start MCP Toolbox (port 5000)
Write-Host "Starting MCP Toolbox on port 5000..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectPath'; Write-Host 'MCP TOOLBOX (Port 5000)' -ForegroundColor Cyan; Get-Content .env | ForEach-Object { if (`$_ -match '^([^#][^=]*)=(.*)$') { [System.Environment]::SetEnvironmentVariable(`$matches[1].Trim(), `$matches[2].Trim()) } }; .\toolbox.exe --tools-file tools.yaml"

# Wait for toolbox to initialize
Write-Host "Waiting 3 seconds for Toolbox to initialize..."
Start-Sleep -Seconds 3

# Start all agents together with A2A enabled (port 8000)
Write-Host "Starting all agents on port 8000 with A2A..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$starterPath'; Write-Host 'ALL AGENTS (Port 8000)' -ForegroundColor Cyan; python -m google.adk.cli web --a2a"

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  All services started!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Access URLs:" -ForegroundColor Cyan
Write-Host "  MCP Toolbox:   http://localhost:5000"
Write-Host "  Web UI:        http://localhost:8000"
Write-Host ""
Write-Host "A2A Endpoints:" -ForegroundColor Cyan
Write-Host "  Deposit Agent: http://localhost:8000/a2a/deposit"
Write-Host "  Loan Agent:    http://localhost:8000/a2a/loan"
Write-Host "  Manager Agent: http://localhost:8000/a2a/manager"
Write-Host ""
Write-Host "Select agent from dropdown in Web UI to test."
