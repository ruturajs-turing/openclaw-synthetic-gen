"""Embed and store all batch2_memory_v3 tasks directly into LanceDB."""
import json
from pathlib import Path
from embedding_store import EmbeddingStore, _task_to_text

BATCH_SIZE = 100  # embed in chunks to avoid API timeouts

tasks = json.loads(Path('outputs/batch2_memory_v3/tasks_all.json').read_text(encoding='utf-8'))
print(f'Loaded {len(tasks)} batch2 tasks')

store = EmbeddingStore()
before = store.get_stats()['total_embeddings']
print(f'LanceDB before: {before} embeddings')

total_stored = 0
for i in range(0, len(tasks), BATCH_SIZE):
    chunk = tasks[i:i + BATCH_SIZE]
    texts = [_task_to_text(t) for t in chunk]
    embeddings = store.embed_texts(texts)

    rows = []
    for task, vec in zip(chunk, embeddings):
        rows.append({
            'task_id': task.get('task_id', ''),
            'persona_id': task.get('persona_id', ''),
            'text_fingerprint': _task_to_text(task)[:500],
            'vector': vec,
        })

    store.table.add(rows)
    total_stored += len(rows)
    print(f'  Stored {total_stored}/{len(tasks)} tasks...', flush=True)

after = store.get_stats()['total_embeddings']
print(f'LanceDB after:  {after} embeddings')
print(f'Added: {after - before} new embeddings')
print('Done.')
