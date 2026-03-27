# Load environment variables from .env file
Get-Content .env | ForEach-Object {
    if ($_ -match "^([^#][^=]*)=(.*)$") {
        [System.Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim())
    }
}

# Start the toolbox
Write-Host "Starting MCP Toolbox on port 5000..."
.\toolbox.exe --tools-file tools.yaml
