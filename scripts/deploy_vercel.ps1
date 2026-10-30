# Static Vercel deploy (Streamlit app.py is ignored by deploying from web/).
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
python scripts/sync_web_data.py
Set-Location web
vercel --prod
