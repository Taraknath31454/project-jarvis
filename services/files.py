import os
import re
import time
from core.config import expand_path

class FileSearch:
    def __init__(self, root, config):
        self.root, self.config = root, config
        self.results = []

    def find(self, query):
        query = re.sub(r'^my\s+', '', query, flags=re.I)
        extension = '.pdf' if re.match(r'PDF(?: named)?\s+', query, re.I) else None
        query = re.sub(r'^PDF(?: named)?\s+', '', query, flags=re.I) if extension else query
        words = re.findall(r'\w+', query.lower())
        if not words:
            raise ValueError('Please give a filename to search for.')
        self.results = []
        visited = 0
        seen = set()
        deadline = time.monotonic() + 8
        limit = int(self.config['max_results'])
        truncated = False
        for value in self.config['roots']:
            base = expand_path(value, self.root)
            if not base.is_dir():
                continue
            for parent, dirs, files in os.walk(base, followlinks=False):
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('node_modules', '__pycache__')
                           and not os.path.islink(os.path.join(parent, d))
                           and not os.path.isjunction(os.path.join(parent, d))]
                for name in dirs + files:
                    visited += 1
                    if visited > int(self.config['max_entries']) or time.monotonic() > deadline:
                        truncated = True
                        break
                    path = os.path.join(parent, name)
                    if all(word in name.lower() for word in words) and (not extension or name.lower().endswith(extension)) and path not in seen:
                        seen.add(path)
                        self.results.append(path)
                        if len(self.results) >= limit:
                            truncated = True
                            break
                if truncated:
                    break
            if truncated:
                break
        if not self.results:
            return 'No matches found in configured folders.' + (' Search limit reached.' if truncated else '')
        return ('Matching results (nothing was opened):\n' + '\n'.join(f'{i}. {p}' for i, p in enumerate(self.results, 1))
                + ('\nSearch limit reached; narrow your query.' if truncated else '')
                + '\nUse “open result 1” to reveal a result in File Explorer.')
