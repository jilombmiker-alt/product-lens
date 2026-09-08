#!/usr/bin/env python3
"""Check repository packaging. Does not execute skills, models or product trials."""
import ast
import json
import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills/product-lens'


def main():
    errors = []
    entry = (SKILL / 'SKILL.md').read_text(encoding='utf-8')
    frontmatter = re.match(r'\A---\n(.*?)\n---\n', entry, re.S)
    if not frontmatter:
        errors.append('Missing SKILL.md frontmatter')
    else:
        metadata = dict(re.findall(r'^(name|description):\s*(.+)$', frontmatter.group(1), re.M))
        if metadata.get('name') != SKILL.name:
            errors.append('Skill folder and name must match')
        if not metadata.get('description', '').strip('" '):
            errors.append('Missing skill description')
    for rel in ['agents/openai.yaml', 'references/trial.md', 'references/design.md',
                'references/handoff.md', 'scripts/check_handoff.py',
                'templates/run-card.json', 'templates/handoff.json']:
        if not (SKILL / rel).is_file():
            errors.append('Missing skill resource: ' + rel)
    links = 0
    files = [p for p in ROOT.rglob('*') if p.is_file() and '.git' not in p.relative_to(ROOT).parts
             and '__pycache__' not in p.relative_to(ROOT).parts]
    for path in files:
        if path.suffix == '.md':
            text = path.read_text(encoding='utf-8')
            if len(re.findall(r'^```', text, re.M)) % 2:
                errors.append('Unclosed code fence: ' + str(path.relative_to(ROOT)))
            for href in re.findall(r'\]\(([^)]+)\)', text):
                if href.startswith(('https://', 'http://', 'mailto:', '#')):
                    continue
                links += 1
                target = (path.parent / unquote(href.split('#')[0])).resolve()
                if not target.is_relative_to(ROOT) or not target.exists():
                    errors.append('Invalid local link: ' + str(path.relative_to(ROOT)) + ' → ' + href)
            for block in re.findall(r'```json\n(.*?)\n```', text, re.S):
                try:
                    json.loads(block)
                except json.JSONDecodeError as exc:
                    errors.append(str(path.relative_to(ROOT)) + ': ' + str(exc))
        if path.suffix == '.json':
            json.loads(path.read_text(encoding='utf-8'))
        if path.suffix == '.py':
            ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        if path.suffix in {'.md', '.yaml', '.yml', '.json', '.py'}:
            text = path.read_text(encoding='utf-8')
            # Packaging guard, not a comprehensive secret detector.
            if re.search(r'/' + r'(?:Users/[^/\s]+/|var/folders/)|github_pat_[A-Za-z0-9_]{20,}|ghp_[A-Za-z0-9]{20,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----', text):
                errors.append('Local path or credential-like content: ' + str(path.relative_to(ROOT)))
    print(json.dumps({'scope': 'package_structure_only', 'files': len(files), 'relative_links': links,
                      'errors': errors, 'product_behavior_verified': False}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
