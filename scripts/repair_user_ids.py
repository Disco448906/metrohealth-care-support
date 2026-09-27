import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database.connection import get_db

def repair():
    db = get_db()
    users = list(db["users"].find({}))
    print(f"Repairing user IDs for {len(users)} registered users...")

    for u in users:
        mongo_id = str(u["_id"])
        custom_id = str(u.get("id", ""))
        email = u.get("email", "")
        name = u.get("name", "")

        id_set = [cid for cid in [mongo_id, custom_id, email] if cid]

        # Update tickets matching name or email or mongo_id or custom_id
        res_t = db["tickets"].update_many(
            {"$or": [
                {"customer_name": name},
                {"customer_id": {"$in": id_set}}
            ]},
            {"$set": {"customer_id": custom_id or mongo_id}}
        )

        res_c = db["complaints"].update_many(
            {"$or": [
                {"customer_name": name},
                {"customer_id": {"$in": id_set}}
            ]},
            {"$set": {"customer_id": custom_id or mongo_id}}
        )

        print(f"User '{name}' ({email}): updated {res_t.modified_count} tickets, {res_c.modified_count} complaints.")

if __name__ == "__main__":
    repair()
