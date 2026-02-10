# Music Taste Genome -- run.ps1
# Usage:
#   .\run.ps1 auth
#   .\run.ps1 collect
#   .\run.ps1 analyze --genome path\to\findings.json
#   .\run.ps1 full --genome path\to\findings.json

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
python "$scriptDir\scripts\run.py" @args
