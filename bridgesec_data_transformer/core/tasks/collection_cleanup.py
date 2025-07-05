# from pymongo import MongoClient
# from datetime import datetime, timedelta
# import os, re
# from celery import shared_task
# from dotenv import load_dotenv

# load_dotenv()

# @shared_task
# def delete_old_collections():

#     mongo_uri = os.getenv("MONGO_URI")
#     db_name = os.getenv("MONGO_DB_NAME")

#     pattern = re.compile(r"bridgesec_(\d{4})_(\d{2})_(\d{2})")
#     cutoff_date = datetime.now() - timedelta(days=15)

#     client = MongoClient(mongo_uri)
#     db = client[db_name]

#     for collection_name in db.list_collection_names():
#         match = pattern.match(collection_name)
#         if match:
#             year, month, day = map(int, match.groups())
#             collection_date = datetime(year, month, day)

#             if collection_date < cutoff_date:
#                 db.drop_collection(collection_name)
#                 print(f"[🗑️] Dropped: {collection_name}")

#     print("[✅] Cleanup done")
