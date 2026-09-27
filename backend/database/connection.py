import os
import json
import threading
from bson import json_util
from dotenv import load_dotenv
import pymongo
import mongomock

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/metrohealth_db")

_db_instance = None
_client_instance = None
_fallback_lock = threading.RLock()
_fallback_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mongo_fallback.json")


def _save_fallback_database():
    """Persist the mongomock demo database atomically between backend restarts."""
    if _db_instance is None or not isinstance(_client_instance, mongomock.MongoClient):
        return
    with _fallback_lock:
        os.makedirs(os.path.dirname(_fallback_file), exist_ok=True)
        snapshot = {
            name: list(_db_instance[name].find({}))
            for name in _db_instance.list_collection_names()
        }
        temp_file = f"{_fallback_file}.tmp"
        with open(temp_file, "w", encoding="utf-8") as output:
            output.write(json_util.dumps(snapshot, ensure_ascii=False))
        os.replace(temp_file, _fallback_file)


def _enable_fallback_persistence():
    """Restore saved data and save after every supported collection mutation."""
    if os.path.exists(_fallback_file):
        try:
            with open(_fallback_file, "r", encoding="utf-8") as source:
                snapshot = json_util.loads(source.read())
            for name, documents in snapshot.items():
                if documents:
                    _db_instance[name].insert_many(documents)
        except Exception as exc:
            print(f"Could not restore local database snapshot ({exc}); starting with empty demo storage.")

    for name in _db_instance.list_collection_names():
        collection = _db_instance[name]
        for method_name in ("insert_one", "insert_many", "update_one", "update_many", "replace_one", "delete_one", "delete_many", "find_one_and_update"):
            original = getattr(collection, method_name)

            def persist_after_write(*args, _original=original, **kwargs):
                result = _original(*args, **kwargs)
                _save_fallback_database()
                return result

            setattr(collection, method_name, persist_after_write)

def get_db():
    global _db_instance, _client_instance
    if _db_instance is not None:
        return _db_instance

    # Try connecting to real MongoDB first
    try:
        if MONGO_URI and not MONGO_URI.startswith("mongodb://localhost"):
            client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=2500)
            client.admin.command('ping')
            _client_instance = client
            _db_instance = client.get_database()
            print("Successfully connected to MongoDB Atlas / Remote Mongo Database.")
            return _db_instance
    except Exception as e:
        print(f"Remote MongoDB connection failed or timeout ({e}). Falling back to local/in-memory database.")

    try:
        client = pymongo.MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=1500)
        client.admin.command('ping')
        _client_instance = client
        _db_instance = client["metrohealth_db"]
        print("Successfully connected to Local MongoDB Server.")
        return _db_instance
    except Exception:
        print("Local MongoDB server unavailable. Initializing persistent Mongomock demo storage.")
        client = mongomock.MongoClient()
        _client_instance = client
        _db_instance = client["metrohealth_db"]
        # Create known collections before patching their writes so their first
        # insert is persisted too. Chat history and staff queues survive restarts.
        for collection_name in (
            "users", "chat_history", "departments", "doctors",
            "doctor_schedules", "appointments", "tickets", "complaints",
        ):
            _db_instance.create_collection(collection_name)
        _enable_fallback_persistence()
        return _db_instance

def get_client():
    get_db()
    return _client_instance
