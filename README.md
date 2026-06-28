# Dapper Threads PDF Generator API

Generates print-ready PDFs with VersaWorks spot color cut paths for card skin orders.

## Deploy to Render.com

1. Upload this folder to a GitHub repo
2. Go to render.com → New Web Service → connect your repo
3. Render auto-detects the Procfile and requirements.txt
4. Add environment variables in the Render dashboard:
   - `SMTP_USER` = your Gmail address (e.g. erika@dapperthreadsus.com)
   - `SMTP_PASS` = your Gmail App Password (not your regular password)

## Getting a Gmail App Password
1. Go to myaccount.google.com → Security → 2-Step Verification (enable if not on)
2. Then go to Security → App passwords
3. Create one for "Mail" → copy the 16-character password
4. Paste it as SMTP_PASS in Render

## PDF Output
Each PDF contains:
- Customer photo filling full 87.6 × 56mm bleed area
- PerfCutContour (green) = outer edge full cut through
- CutContour (magenta) = card edge kiss cut  
- CutContour (magenta) = chip hole kiss cut

Drop directly into VersaWorks 6.
