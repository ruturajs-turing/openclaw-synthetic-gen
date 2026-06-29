import json, random

tasks = json.load(open('outputs/batch2_memory_v3/tasks_all.json', encoding='utf-8'))
random.seed(99)
sample = random.sample(tasks, 7)

for t in sample:
    print('='*70)
    print(f"Task:  {t['task_id']}  |  {t['task_title']}")
    print(f"Goal:  {t['goal_summary']}")
    print(f"Data:  {t['data_levels']}  |  Jailbreak: {t['jailbreak_vector']}")
    print("Milestones:")
    for i, m in enumerate(t.get('conversation_arc', []), 1):
        gate = m.get('privacy_gate') or 'none'
        intent = m.get('user_intent') or ''
        intent_short = intent[:130] + '...' if len(intent) > 130 else intent
        gate_short = gate[:110] + '...' if len(gate) > 110 else gate
        print(f"  {i}. {m['milestone']}")
        print(f"     > {intent_short}")
        print(f"     Gate: {gate_short}")
    print()
