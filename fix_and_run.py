"""Fix broken save scripts by executing them with Django pre-configured."""
import os, sys, re, glob, subprocess

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'the_80_percent_bill.settings')
os.environ.setdefault('DEBUG', 'true')
sys.path.insert(0, '/Users/adamlinssen/Desktop/the80percentbill')

import django
django.setup()

from reps.models import Representative

failed = []
for script_path in sorted(glob.glob('save_*.py')):
    with open(script_path) as f:
        content = f.read()

    # Skip scripts that already have proper django.setup() ordering
    setup_line = None
    import_line = None
    for i, line in enumerate(content.split('\n')):
        if 'django.setup()' in line and setup_line is None:
            setup_line = i
        if 'from reps.models' in line and import_line is None:
            import_line = i
    if setup_line is not None and import_line is not None and setup_line < import_line:
        continue

    # This script has broken ordering - fix it by prepending Django setup
    # and removing the broken import lines
    fixed = "import os, sys\n"
    fixed += "os.environ['DJANGO_SETTINGS_MODULE'] = 'the_80_percent_bill.settings'\n"
    fixed += "os.environ['DEBUG'] = 'true'\n"
    fixed += f"sys.path.insert(0, '{os.path.dirname(os.path.abspath(script_path))}')\n"
    fixed += "import django\ndjango.setup()\n\n"

    # Remove original broken imports and setup attempts, keep everything else
    for line in content.split('\n'):
        # Skip lines that are now handled by our prefix
        if any(skip in line for skip in [
            'import django', 'django.setup()',
            'DJANGO_SETTINGS_MODULE', 'sys.path.insert',
            "os.environ['DEBUG']", 'os.environ.setdefault',
        ]):
            continue
        if line.strip().startswith('from reps.models') or line.strip().startswith('from django'):
            # Move these after setup by including them
            fixed += line + '\n'
            continue
        fixed += line + '\n'

    # Write temp file and run it
    tmp_path = f'_tmp_{script_path}'
    with open(tmp_path, 'w') as f:
        f.write(fixed)

    result = subprocess.run(
        [sys.executable, tmp_path],
        capture_output=True, text=True, timeout=30
    )
    os.remove(tmp_path)

    if result.returncode != 0:
        print(f"FAIL {script_path}: {result.stderr.strip().split(chr(10))[-1]}")
        failed.append((script_path, result.stderr.strip().split('\n')[-1]))
    else:
        output = result.stdout.strip()
        if output:
            print(f"  {script_path}: {output.split(chr(10))[0]}")
        else:
            print(f"  {script_path}: (no output)")

if failed:
    print(f"\nFailed ({len(failed)}):")
    for path, reason in failed:
        print(f"  {path}: {reason}")
else:
    print("\nAll scripts processed successfully!")
