import re
import os,django
from django.conf import settings
from datetime import datetime, timedelta,timezone
from pymongo import MongoClient


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bridgesec_data_transformer.settings")
django.setup()

MONGO_URI = settings.MONGO_URI
client = MongoClient(MONGO_URI)


pattern = re.compile(r"^bridgesec_(\d{4}-\d{2}-\d{2}T\d{4})$")

# Time window: from 15 days ago up to now
now = datetime.now(timezone.utc)
cutoff = now.replace(day=1)
cutoff_2_months_ago = (cutoff.replace(day=1) - timedelta(days=1)).replace(day=1) 

deleted_dbs = []


for db_name in client.list_database_names():
    match = pattern.match(db_name)
    if match:
        date_str = match.group(1)  # Extract "2025-07-15T1941"
        try:
            db_datetime = datetime.strptime(date_str, "%Y-%m-%dT%H%M").replace(tzinfo=timezone.utc)
            if db_datetime < cutoff_2_months_ago:
                client.drop_database(db_name)
                deleted_dbs.append(db_name)
                print(f" Dropped DB: {db_name}")
        except ValueError:
            print(f" Skipped invalid datetime in DB name: {db_name}")
    else:
        print(f" Skipped unmatched DB name: {db_name}")


print(f"\n Total dropped databases: {len(deleted_dbs)}")