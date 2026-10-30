"""Developer-only check of the trusted, bundled examples. NOT a student execution API.

Run after reviewing changes to build_curriculum.py. Public student submissions must
always go through sandbox_runner; never point this script at uploaded code.
"""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / 'public' / 'learning-data.json').read_text())
COMMANDS = {
 'python': ('main.py', None, [sys.executable, '-I', 'main.py']),
 'javascript': ('main.js', None, ['node', 'main.js']),
 'ruby': ('main.rb', None, ['ruby', 'main.rb']),
 'sql': ('main.sql', None, ['sqlite3', '-batch', '-header', '-column', ':memory:', '.read main.sql']),
 'cpp': ('main.cpp', ['clang++', '-std=c++17', 'main.cpp', '-o', 'program'], ['./program']),
 'c': ('main.c', ['clang', '-std=c17', 'main.c', '-o', 'program'], ['./program']),
 'java': ('Main.java', ['javac', 'Main.java'], ['java', '-cp', '.', 'Main']),
 'go': ('main.go', ['go', 'build', '-o', 'program', 'main.go'], ['./program']),
}
seen=set(); failures=[]; checked=0; skipped=[]
for item in DATA['lessons']+DATA['examples']+DATA['algorithms']:
    lang=item['language']; key=(lang,item['code'],item['stdin'])
    if key in seen: continue
    seen.add(key)
    filename, compiler, runner = COMMANDS[lang]
    if not shutil.which((compiler or runner)[0]):
        skipped.append(item['id']);continue
    with tempfile.TemporaryDirectory(prefix='campus-curriculum-check-') as directory:
        (Path(directory)/filename).write_text(item['code'])
        try:
            if compiler:
                result=subprocess.run(compiler,cwd=directory,capture_output=True,text=True,timeout=40)
                if result.returncode: raise ValueError(result.stderr)
            result=subprocess.run(runner,cwd=directory,input=item['stdin'],capture_output=True,text=True,timeout=8)
            if result.returncode: raise ValueError(result.stderr)
            def normalize(value):
                return '\n'.join(' '.join(line.split()) for line in value.strip().splitlines())
            if normalize(result.stdout)!=normalize(item['output']):
                raise ValueError(f"expected {item['output']!r}, received {result.stdout!r}")
            checked+=1
        except (ValueError,subprocess.TimeoutExpired) as error:
            failures.append((item['id'],str(error)))
print(f'{checked} unique bundled programs passed; {len(failures)} failed; {len(skipped)} skipped.')
for name,error in failures: print(name+': '+error)
if skipped: print('Unavailable toolchains: '+', '.join(skipped))
sys.exit(1 if failures or skipped else 0)
