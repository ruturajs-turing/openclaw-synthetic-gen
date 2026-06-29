"""Remove stale batch-2 (seq >= 6) entries from LanceDB, keeping only batch-1 baselines."""
import re
import lancedb
from config import LANCEDB_PATH

db = lancedb.connect(str(LANCEDB_PATH))
tbl = db.open_table("task_embeddings")

results = tbl.search().select(["task_id"]).limit(5000).to_list()
print(f"Total entries before cleanup: {len(results)}")

stale_ids = []
for r in results:
    tid = str(r.get("task_id", ""))
    m = re.search(r"-(\d+)$", tid)
    if m and int(m.group(1)) >= 6:
        stale_ids.append(tid)

print(f"Stale batch-2 entries to remove: {len(stale_ids)}")

for tid in stale_ids:
    tbl.delete(f"task_id = '{tid}'")

remaining = tbl.search().select(["task_id"]).limit(5000).to_list()
print(f"Remaining entries after cleanup: {len(remaining)}")
print("Done.")
