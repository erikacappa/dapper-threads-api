services:
  - type: web
    name: dapper-threads-pdf-api
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn app:app --timeout 120
    envVars:
      - key: SMTP_USER
        sync: false   # set manually in Render dashboard
      - key: SMTP_PASS
        sync: false   # set manually in Render dashboard
