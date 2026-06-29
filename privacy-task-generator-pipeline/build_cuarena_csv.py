"""
Reusable CUArena CSV builder.

Converts tasks_all.json from any batch into the standard CUArena upload format.

Usage:
    python build_cuarena_csv.py <batch_output_dir>

Example:
    python build_cuarena_csv.py outputs/batch4
    python build_cuarena_csv.py outputs/batch5
"""

import json, csv, re, sys
from pathlib import Path

# ─── CUArena Upload Column Schema ───────────────────────────────────────────
CUARENA_COLUMNS = [
    'task_id',           # T-XXXX-YY format
    'title',             # from task_title
    'domain',            # from domain
    'category',          # from subdomain
    'complexity',        # simple | moderate | complex | expert
    'estimated_turns',   # len(conversation_arc)
    'goal_summary',      # from goal_summary
    'opening_message',   # conversation_arc[0].user_intent
    'milestones',        # pipe-separated milestone names from conversation_arc
    'suggested_skills',  # pipe-separated openclaw_skills
    'eta',               # derived from complexity_tier
    'reward',            # derived from complexity_tier
]

# ─── Mapping helpers ─────────────────────────────────────────────────────────
COMPLEXITY_LABELS = {1: 'simple', 2: 'moderate', 3: 'complex', 4: 'expert', 5: 'expert'}
ETA_MAP = {1: '10 min', 2: '15 min', 3: '20 min', 4: '25 min', 5: '30 min'}
REWARD_MAP = {1: 1.0, 2: 2.0, 3: 3.0, 4: 4.0, 5: 5.0}


def to_cuarena_id(internal_id: str) -> str:
    return internal_id.replace('P-', 'T-')


def numeric_sort_key(task: dict):
    m = re.match(r'P-(\d+)-(\d+)', task['task_id'])
    if m:
        return (int(m.group(1)), int(m.group(2)))
    return (0, 0)


def build_row(task: dict) -> dict:
    arc = task.get('conversation_arc', [])
    milestones = ' | '.join(m.get('milestone', '') for m in arc if m.get('milestone'))
    opening = arc[0].get('user_intent', '') if arc else ''
    skills = task.get('openclaw_skills', [])
    skills_str = ' | '.join(skills) if isinstance(skills, list) else str(skills)
    tier = task.get('complexity_tier', 2)
    if not isinstance(tier, int):
        tier = 2

    return {
        'task_id': to_cuarena_id(task['task_id']),
        'title': task.get('task_title', ''),
        'domain': task.get('domain', ''),
        'category': task.get('subdomain', ''),
        'complexity': COMPLEXITY_LABELS.get(tier, 'moderate'),
        'estimated_turns': len(arc),
        'goal_summary': task.get('goal_summary', ''),
        'opening_message': opening,
        'milestones': milestones,
        'suggested_skills': skills_str,
        'eta': ETA_MAP.get(tier, '15 min'),
        'reward': REWARD_MAP.get(tier, 2.0),
    }


def build_cuarena_csv(batch_dir: Path, output_name: str = 'cuarena_upload_tasks_all.csv') -> Path:
    tasks_file = batch_dir / 'tasks_all.json'
    if not tasks_file.exists():
        raise FileNotFoundError(f"No tasks_all.json in {batch_dir}")

    all_tasks = json.loads(tasks_file.read_text(encoding='utf-8'))
    all_tasks.sort(key=numeric_sort_key)

    csv_path = batch_dir / output_name
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=CUARENA_COLUMNS)
        w.writeheader()
        for t in all_tasks:
            w.writerow(build_row(t))

    return csv_path, len(all_tasks)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <batch_output_dir>")
        sys.exit(1)

    batch_dir = Path(sys.argv[1])
    csv_path, count = build_cuarena_csv(batch_dir)
    print(f"CUArena CSV written: {csv_path} ({count} rows)")
    print(f"Columns: {CUARENA_COLUMNS}")
