# the80percentbill

Django app for the 80% Bill project.

## Development

```bash
# Activate venv
source venv/bin/activate

# Run development server on port 8000
python manage.py runserver 8000

# Or use VS Code debugger (port 8000 configured in .vscode/launch.json)
```

## Environment

Copy `.env.example` to `.env` and configure:
- Geocodio API key
- Supabase credentials
- DEBUG mode
