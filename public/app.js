const $ = (id) => document.getElementById(id);
const languages = {
  "python": {
    "name": "Python",
    "icon": "Py",
    "file": "main.py",
    "version": "Python 3",
    "compiled": false
  },
  "cpp": {
    "name": "C++",
    "icon": "C+",
    "file": "main.cpp",
    "version": "C++17",
    "compiled": true
  },
  "c": {
    "name": "C",
    "icon": "C",
    "file": "main.c",
    "version": "C17",
    "compiled": true
  },
  "javascript": {
    "name": "JavaScript",
    "icon": "JS",
    "file": "main.js",
    "version": "JavaScript \u00b7 Node.js",
    "compiled": false
  },
  "java": {
    "name": "Java",
    "icon": "Ja",
    "file": "Main.java",
    "version": "Java",
    "compiled": true
  },
  "go": {
    "name": "Go",
    "icon": "Go",
    "file": "main.go",
    "version": "Go",
    "compiled": true
  },
  "ruby": {
    "name": "Ruby",
    "icon": "Rb",
    "file": "main.rb",
    "version": "Ruby",
    "compiled": false
  },
  "sql": {
    "name": "SQL",
    "icon": "SQ",
    "file": "main.sql",
    "version": "SQL \u00b7 SQLite",
    "compiled": false
  }
};
const starters = {
  python: '# Welcome to Campus Code!\n# A small beginning. Endless possibilities.\n\nprint("Hello, world!")\n\n# Try something of your own\nname = "curious mind"\nprint(f"Welcome, {name}. Let’s start building!")\n',
  cpp: '// Welcome to Campus Code!\n// A small beginning. Endless possibilities.\n\n#include <iostream>\n#include <string>\nusing namespace std;\n\nint main() {\n    cout << "Hello, world!" << endl;\n\n    string name = "curious mind";\n    cout << "Welcome, " << name << ". Let’s start building!" << endl;\n    return 0;\n}\n'
};
Object.assign(starters, {
  "c": "// Welcome to Campus Code!\n#include <stdio.h>\n\nint main(void) {\n    printf(\"Hello, world!\\n\");\n    for (int n = 1; n <= 5; n++) {\n        printf(\"%d squared is %d\\n\", n, n * n);\n    }\n    return 0;\n}\n",
  "javascript": "// Welcome to Campus Code!\nconsole.log(\"Hello, world!\");\n\nconst name = \"curious mind\";\nconsole.log(`Welcome, ${name}. Let\u2019s start building!`);\n\nfor (let n = 1; n <= 5; n++) {\n    console.log(`${n} squared is ${n * n}`);\n}\n",
  "java": "// Welcome to Campus Code!\npublic class Main {\n    public static void main(String[] args) {\n        System.out.println(\"Hello, world!\");\n        for (int n = 1; n <= 5; n++) {\n            System.out.println(n + \" squared is \" + n * n);\n        }\n    }\n}\n",
  "go": "// Welcome to Campus Code!\npackage main\n\nimport \"fmt\"\n\nfunc main() {\n    fmt.Println(\"Hello, world!\")\n    for n := 1; n <= 5; n++ {\n        fmt.Printf(\"%d squared is %d\\n\", n, n*n)\n    }\n}\n",
  "ruby": "# Welcome to Campus Code!\nputs \"Hello, world!\"\n\nname = \"curious mind\"\nputs \"Welcome, #{name}. Let\u2019s start building!\"\n\n(1..5).each do |n|\n    puts \"#{n} squared is #{n * n}\"\nend\n",
  "sql": "-- Welcome to Campus Code!\n-- Each run starts with a fresh in-memory database.\nCREATE TABLE students (name TEXT, score INTEGER);\nINSERT INTO students VALUES\n    ('Alex', 92),\n    ('Sam', 85),\n    ('Jordan', 97);\n\nSELECT name, score\nFROM students\nWHERE score >= 90\nORDER BY score DESC;\n"
});
const examples = {
 python: [
  ['Hello, world!', 'Your first program', starters.python],
  ['Meet your program', 'Read user input', 'name = input("What is your name? ")\nprint(f"Hello, {name}!")\n', 'Alex'],
  ['The Fibonacci sequence', 'Explore a loop', 'a, b = 0, 1\nfor i in range(10):\n    print(a, end=" ")\n    a, b = b, a + b\nprint()\n'],
  ['A little number magic', 'Functions & lists', 'def square(number):\n    return number * number\n\nfor n in range(1, 6):\n    print(f"{n} squared is {square(n)}")\n']
 ],
 cpp: [
  ['Hello, world!', 'Your first program', starters.cpp],
  ['Meet your program', 'Read user input', '#include <iostream>\n#include <string>\nusing namespace std;\n\nint main() {\n    string name;\n    cout << "What is your name? ";\n    getline(cin, name);\n    cout << "Hello, " << name << "!" << endl;\n    return 0;\n}\n', 'Alex'],
  ['The Fibonacci sequence', 'Explore a loop', '#include <iostream>\nusing namespace std;\n\nint main() {\n    int a = 0, b = 1;\n    for (int i = 0; i < 10; i++) {\n        cout << a << " ";\n        int next = a + b;\n        a = b;\n        b = next;\n    }\n    cout << endl;\n    return 0;\n}\n'],
  ['A little number magic', 'Functions & loops', '#include <iostream>\nusing namespace std;\n\nint square(int n) { return n * n; }\n\nint main() {\n    for (int n = 1; n <= 5; n++)\n        cout << n << " squared is " << square(n) << endl;\n    return 0;\n}\n']
 ]
};
Object.assign(examples, {
  "c": [
    [
      "Hello, world!",
      "Your first program",
      "// Welcome to Campus Code!\n#include <stdio.h>\n\nint main(void) {\n    printf(\"Hello, world!\\n\");\n    for (int n = 1; n <= 5; n++) {\n        printf(\"%d squared is %d\\n\", n, n * n);\n    }\n    return 0;\n}\n"
    ],
    [
      "Double a number",
      "Read user input",
      "#include <stdio.h>\n\nint main(void) {\n    int number;\n    printf(\"Enter a number: \");\n    if (scanf(\"%d\", &number) == 1)\n        printf(\"Double is %d\\n\", number * 2);\n    return 0;\n}\n",
      "21"
    ]
  ],
  "javascript": [
    [
      "Hello, world!",
      "Your first program",
      "// Welcome to Campus Code!\nconsole.log(\"Hello, world!\");\n\nconst name = \"curious mind\";\nconsole.log(`Welcome, ${name}. Let\u2019s start building!`);\n\nfor (let n = 1; n <= 5; n++) {\n    console.log(`${n} squared is ${n * n}`);\n}\n"
    ],
    [
      "Double a number",
      "Read user input",
      "const fs = require(\"node:fs\");\nconst number = Number(fs.readFileSync(0, \"utf8\").trim());\nconsole.log(`Double is ${number * 2}`);\n",
      "21"
    ]
  ],
  "java": [
    [
      "Hello, world!",
      "Your first program",
      "// Welcome to Campus Code!\npublic class Main {\n    public static void main(String[] args) {\n        System.out.println(\"Hello, world!\");\n        for (int n = 1; n <= 5; n++) {\n            System.out.println(n + \" squared is \" + n * n);\n        }\n    }\n}\n"
    ],
    [
      "Double a number",
      "Read user input",
      "import java.util.Scanner;\n\npublic class Main {\n    public static void main(String[] args) {\n        Scanner scanner = new Scanner(System.in);\n        int number = scanner.nextInt();\n        System.out.println(\"Double is \" + number * 2);\n    }\n}\n",
      "21"
    ]
  ],
  "go": [
    [
      "Hello, world!",
      "Your first program",
      "// Welcome to Campus Code!\npackage main\n\nimport \"fmt\"\n\nfunc main() {\n    fmt.Println(\"Hello, world!\")\n    for n := 1; n <= 5; n++ {\n        fmt.Printf(\"%d squared is %d\\n\", n, n*n)\n    }\n}\n"
    ],
    [
      "Double a number",
      "Read user input",
      "package main\n\nimport \"fmt\"\n\nfunc main() {\n    var number int\n    fmt.Scan(&number)\n    fmt.Println(\"Double is\", number*2)\n}\n",
      "21"
    ]
  ],
  "ruby": [
    [
      "Hello, world!",
      "Your first program",
      "# Welcome to Campus Code!\nputs \"Hello, world!\"\n\nname = \"curious mind\"\nputs \"Welcome, #{name}. Let\u2019s start building!\"\n\n(1..5).each do |n|\n    puts \"#{n} squared is #{n * n}\"\nend\n"
    ],
    [
      "Double a number",
      "Read user input",
      "number = gets.to_i\nputs \"Double is #{number * 2}\"\n",
      "21"
    ]
  ],
  "sql": [
    [
      "Student results",
      "Tables & filtering",
      "-- Welcome to Campus Code!\n-- Each run starts with a fresh in-memory database.\nCREATE TABLE students (name TEXT, score INTEGER);\nINSERT INTO students VALUES\n    ('Alex', 92),\n    ('Sam', 85),\n    ('Jordan', 97);\n\nSELECT name, score\nFROM students\nWHERE score >= 90\nORDER BY score DESC;\n"
    ],
    [
      "A little number magic",
      "Common table expressions",
      "WITH numbers(n) AS (\n    VALUES (1), (2), (3), (4), (5)\n)\nSELECT n AS number, n * n AS squared\nFROM numbers;\n"
    ]
  ]
});
let language = 'python', running = false, toastTimer, saveTimer;
const pendingSaves = new Map();
let saveChain = Promise.resolve();
const drafts = {};
const savedLabel = () => 'Workspace draft saved';
function read(key, fallback) { try { return localStorage.getItem(key) ?? fallback; } catch { return fallback; } }
function store(key, value) { try { localStorage.setItem(key, value); } catch { /* Preferences remain in memory if browser storage is blocked. */ } }
function save() {
 if (!window.campusWorkspace.user) return;
 drafts[language] = {code: $('editor').value, stdin: $('stdin').value};
 pendingSaves.set(language, {...drafts[language]});
 $('saved').textContent = 'Unsaved changes'; clearTimeout(saveTimer);
 saveTimer = setTimeout(() => flushDrafts().catch(() => {}), 800);
}
async function flushDrafts() {
 clearTimeout(saveTimer);
 saveChain = saveChain.catch(() => {}).then(async () => {
  for (const [id, draft] of [...pendingSaves]) {
   try {
    await window.api(`/api/drafts/${id}`, {method: 'PUT', body: draft});
    if (pendingSaves.get(id) === draft) pendingSaves.delete(id);
   } catch (error) { $('saved').textContent = 'Save failed · ' + error.message; throw error; }
  }
  $('saved').textContent = pendingSaves.size ? 'Unsaved changes' : savedLabel();
 });
 return saveChain;
}
window.flushDrafts = flushDrafts;
window.addEventListener('beforeunload', event => { if (pendingSaves.size) { event.preventDefault(); event.returnValue = ''; } });
function updateLines() { $('lineNumbers').textContent = Array.from({length: $('editor').value.split('\n').length}, (_, i) => i + 1).join('\n'); updateCursor(); }
function updateCursor() { const before = $('editor').value.slice(0, $('editor').selectionStart).split('\n'); $('cursor').textContent = `Ln ${before.length}, Col ${before.at(-1).length + 1}`; }
function tab(name) { for (const item of ['output','input']) { $(`${item}Tab`).classList.toggle('active', item === name); $(`${item}Tab`).setAttribute('aria-selected', item === name); $(`${item}Panel`).hidden = item !== name; } }
function clearOutput() { $('output').textContent = ''; $('output').hidden = true; $('emptyOutput').hidden = false; $('runStatus').innerHTML = '<i></i> Ready when you are'; $('duration').textContent = '—'; }
function changeLanguage(next) {
 if (running) return;
 if (drafts[language]) save();
 language = next;
 let draft = drafts[language];

 if (!draft || typeof draft.code !== 'string') draft = {code: starters[language], stdin: ''};
 drafts[language] = draft;
 $('editor').value = draft.code; $('stdin').value = draft.stdin || '';
 $('filename').textContent = languages[language].file;
 $('languageVersion').textContent = languages[language].version;
 $('stdin').disabled = language === 'sql';
 $('inputHelp').textContent = language === 'sql' ? 'SQL runs against a fresh SQLite database each time. Create tables and insert data in your source code.' : 'Enter values before running, one per line. Your program reads these from standard input.';
 $('inputNote').textContent = language === 'sql' ? 'Standard input is not used for SQL queries.' : 'Input is sent all at once when the program starts.';
 $('editor').scrollTop = 0; $('lineNumbers').scrollTop = 0;
 document.querySelectorAll('[data-language]').forEach(b => { b.classList.toggle('selected', b.dataset.language === language); b.setAttribute('aria-pressed', b.dataset.language === language); });
 clearOutput(); updateLines(); store('campus-language', language);
 $('saved').textContent = pendingSaves.size ? 'Unsaved changes' : savedLabel();
}
async function run() {
 if (running) return;
 if (!window.campusWorkspace.user) return;
 running = true; save(); tab('output');
 $('run').disabled = true; $('run').innerHTML = '<span>◌</span> Running…';
 document.querySelectorAll('[data-language]').forEach(b => b.disabled = true);
 $('emptyOutput').hidden = true; $('output').hidden = false; $('output').classList.remove('error'); $('output').textContent = languages[language].compiled ? 'Compiling your program…' : 'Running your program…'; $('runStatus').textContent = 'Runner is working'; $('duration').textContent = '…';
 try {
  const result = await window.api('/api/run', {method: 'POST', body: {language, code: $('editor').value, stdin: $('stdin').value}});
  let output = result.stdout;
  if (result.stderr) output += (output && !output.endsWith('\n') ? '\n' : '') + result.stderr;
  if (result.timedOut) output += '\nTime limit reached. Check for an infinite loop.\n';
  if (result.truncated) output += '\n[Output truncated at 128 KB]\n';
  $('output').textContent = output || '(Program finished with no output.)';
  const failed = result.exitCode !== 0 || result.timedOut;
  $('output').classList.toggle('error', failed);
  $('runStatus').textContent = result.timedOut ? 'Time limit reached' : failed ? `${result.phase === 'compile' ? 'Compilation failed' : 'Exited'} · code ${result.exitCode}` : '✓ Finished successfully';
  $('duration').textContent = `${(result.durationMs / 1000).toFixed(2)} s`;
 } catch (error) { $('output').textContent = error.message; $('output').classList.add('error'); $('runStatus').textContent = 'Runner unavailable'; $('duration').textContent = '—'; }
 finally { running = false; $('run').disabled = false; $('run').innerHTML = `<span>▶</span> Run code <kbd>${shortcut} ↵</kbd>`; document.querySelectorAll('[data-language]').forEach(b => b.disabled = false); }
}
function toast(message) { clearTimeout(toastTimer); $('toast').textContent = message; $('toast').hidden = false; toastTimer = setTimeout(() => $('toast').hidden = true, 2800); }
function showExamples() {
 $('exampleList').replaceChildren();
 for (const [title, desc, code, input] of examples[language]) {
  const button = document.createElement('button'); const name = document.createElement('span'), description = document.createElement('small');
  name.textContent = title; description.textContent = desc; button.append(name, description);
  button.onclick = () => { if (running) return; if ($('editor').value !== starters[language] && $('editor').value !== code && !confirm('Replace your current code with this example? Download your code first if you want to keep it.')) return; $('editor').value = code; $('stdin').value = input || ''; save(); updateLines(); clearOutput(); if (input) tab('input'); $('exampleDialog').close(); toast('Example loaded. Make it your own.'); };
  $('exampleList').append(button);
 }
 $('exampleDialog').showModal();
}
const shortcut = /Mac|iPhone|iPad/.test(navigator.platform) ? '⌘' : 'Ctrl';
$('emptyShortcut').textContent = shortcut; $('runShortcut').textContent = `${shortcut} ↵`;
const languageSwitch = document.querySelector('.language-switch');
for (const [id, config] of Object.entries(languages)) {
 const button = document.createElement('button');
 button.dataset.language = id;
 button.setAttribute('aria-label', config.name);
 const icon = document.createElement('span'); icon.className = `language-icon ${id}`; icon.textContent = config.icon;
 button.append(icon, document.createTextNode(config.name));
 button.onclick = () => changeLanguage(id);
 languageSwitch.append(button);
}
$('editor').addEventListener('input', () => { updateLines(); save(); });
$('editor').addEventListener('scroll', () => $('lineNumbers').scrollTop = $('editor').scrollTop);
for (const event of ['click', 'keyup', 'select']) $('editor').addEventListener(event, updateCursor);
$('editor').addEventListener('keydown', event => { if (event.key === 'Tab') { event.preventDefault(); const editor = $('editor'); editor.setRangeText('    ', editor.selectionStart, editor.selectionEnd, 'end'); updateLines(); save(); } });
document.addEventListener('keydown', event => { if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') { event.preventDefault(); run(); } });
$('stdin').addEventListener('input', save);
$('run').onclick = run; $('clear').onclick = () => { if (!running) clearOutput(); };
$('inputTab').onclick = () => tab('input'); $('outputTab').onclick = () => tab('output');
$('reset').onclick = () => { if (running || !confirm('Reset this editor to the starter program? Your current code will be replaced.')) return; $('editor').value = starters[language]; $('stdin').value = ''; save(); updateLines(); clearOutput(); toast('A fresh start.'); };
$('download').onclick = () => { const url = URL.createObjectURL(new Blob([$('editor').value], {type:'text/plain'})); const link = document.createElement('a'); link.href = url; link.download = $('filename').textContent; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); toast('Source file downloaded.'); };
for (const id of ['examples','tryExample']) $(id).onclick = showExamples;
$('closeExamples').onclick = () => $('exampleDialog').close();
$('exampleDialog').addEventListener('click', e => { if (e.target === $('exampleDialog')) { const rect = e.target.getBoundingClientRect(); if (e.clientX < rect.left || e.clientX > rect.right || e.clientY < rect.top || e.clientY > rect.bottom) e.target.close(); } });
document.body.classList.toggle('dark', read('campus-theme', 'light') === 'dark');
$('theme').onclick = () => { document.body.classList.toggle('dark'); store('campus-theme', document.body.classList.contains('dark') ? 'dark' : 'light'); };
window.workspaceReady.then(state => {
 Object.assign(drafts, state.drafts);
 const previousLanguage = read('campus-language', 'python');
 // Avoid saving the empty editor over a loaded workspace draft on first render.
 language = Object.hasOwn(languages, previousLanguage) ? previousLanguage : 'python';
 const initialDraft = drafts[language];
 delete drafts[language];
 changeLanguage(language);
 if (initialDraft) { drafts[language] = initialDraft; $('editor').value = initialDraft.code; $('stdin').value = initialDraft.stdin; updateLines(); }
});

// Public bridge for the learning library; all student code still uses /api/run.
window.campusEditor = {
 async openExample(item) {
  await window.workspaceReady;
  if (running) { toast('Wait for the program to finish.'); return false; }
  if (!Object.hasOwn(languages, item.language)) return false;
  if (drafts[language]) save();
  const target = drafts[item.language];
  if (target && target.code !== starters[item.language] && target.code !== item.code && !confirm('This will replace your current code in this language. Download it first if you want to keep it. Continue?')) return false;
  changeLanguage(item.language);
  $('editor').value = item.code; $('stdin').value = item.stdin || '';
  updateLines(); clearOutput(); tab(item.stdin ? 'input' : 'output'); save();
  location.hash = 'compiler';
  $('editor').focus();
  toast('Example opened in the editor.');
  return true;
 }
};
