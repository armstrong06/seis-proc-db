from seis_proc_db.database import Session
from sqlalchemy import text
import time

# === Configuration ===
CUTOFF_DATE = "2024-01-01"
BATCH_SIZE = 1000
SLEEP_TIME = 0.1  # Optional pause between batches

# === Batch deletion loop ===
total_deleted = 0
with Session() as session:
    while True:
        result = session.execute(
            text(f"""
                DELETE FROM contdatainfo
                WHERE date >= :cutoff
                LIMIT {BATCH_SIZE}
            """),
            {"cutoff": CUTOFF_DATE}
        )
        session.commit()
        deleted = result.rowcount

        if deleted == 0:
            break

        total_deleted += deleted
        print(f"Deleted {deleted} rows... (total so far: {total_deleted})")
        time.sleep(SLEEP_TIME)

print(f"Finished. Total rows deleted: {total_deleted}")
