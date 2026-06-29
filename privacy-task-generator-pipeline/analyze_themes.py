"""Analyze batch1 + batch2 tasks to extract used themes, subdomains, jailbreak vectors, tool combos."""
import json
from pathlib import Path
from collections import Counter

b1_tasks = json.loads(Path('outputs/batch1_no_memory/tasks_all.json').read_text(encoding='utf-8'))
b2_tasks = json.loads(Path('outputs/batch2_memory_v3/tasks_all.json').read_text(encoding='utf-8'))
all_tasks = b1_tasks + b2_tasks
print(f"Analyzing {len(all_tasks)} tasks ({len(b1_tasks)} batch1 + {len(b2_tasks)} batch2)\n")

# 1. Subdomains
subdomains = Counter(t.get('subdomain','').lower() for t in all_tasks)
print("=== TOP SUBDOMAINS (used 10+ times) ===")
for sd, n in subdomains.most_common():
    if n >= 10:
        print(f"  {sd}: {n}")

# 2. Jailbreak vectors
jailbreaks = Counter(t.get('jailbreak_vector','') for t in all_tasks)
print("\n=== JAILBREAK VECTOR DISTRIBUTION ===")
for jb, n in jailbreaks.most_common():
    print(f"  {jb}: {n}")

# 3. Top task title keywords
from collections import defaultdict
import re
word_counts = Counter()
for t in all_tasks:
    title = t.get('task_title', '')
    words = re.findall(r'\b[A-Z][a-z]{3,}\b', title)
    word_counts.update(words)
print("\n=== TOP TITLE KEYWORDS (25+ uses) ===")
for w, n in word_counts.most_common():
    if n >= 25:
        print(f"  {w}: {n}")

# 4. Skills used
skill_counts = Counter()
for t in all_tasks:
    for s in t.get('openclaw_skills', []):
        skill_counts[s] += 1
print("\n=== TOP SKILLS (50+ uses) ===")
for s, n in skill_counts.most_common():
    if n >= 50:
        print(f"  {s}: {n}")

# 5. PII fields used
pii_counts = Counter()
for t in all_tasks:
    for p in t.get('pii_fields_exercised', []):
        pii_counts[p] += 1
print("\n=== TOP PII FIELDS (50+ uses) ===")
for p, n in pii_counts.most_common():
    if n >= 50:
        print(f"  {p}: {n}")

# 6. Domains
domains = Counter(t.get('domain','') for t in all_tasks)
print("\n=== DOMAIN DISTRIBUTION ===")
for d, n in domains.most_common():
    print(f"  {d}: {n}")

# 7. Common task title patterns (detect repeated narrative themes)
print("\n=== MOST REPEATED SUBDOMAIN+DOMAIN COMBOS (20+ times) ===")
combos = Counter((t.get('domain',''), t.get('subdomain','')) for t in all_tasks)
for (d,s), n in combos.most_common():
    if n >= 20:
        print(f"  {d}/{s}: {n}")
