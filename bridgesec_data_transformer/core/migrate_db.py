from pymongo import MongoClient

# ---------------- CONFIG ----------------
LOCAL_MONGO_URI = "mongodb://localhost:27017"
ATLAS_MONGO_URI = "mongodb+srv://palaniselvam:adjecti@bridgesec-cluster.kiigrzg.mongodb.net/?retryWrites=true&w=majority&appName=bridgesec-cluster"

LOCAL_DB_NAME = "bridgesec_2025-09-1"   # source DB (local)
ATLAS_DB_NAME = "bridgesec_2025-09-13T1240"                   # target DB (Atlas)

COLLECTIONS = ["okta_app_oauth", "okta_app_saml"]  # collections to migrate
# ----------------------------------------

# Connect to local + atlas
local_client = MongoClient(LOCAL_MONGO_URI)
local_db = local_client[LOCAL_DB_NAME]

atlas_client = MongoClient(ATLAS_MONGO_URI)
atlas_db = atlas_client[ATLAS_DB_NAME]

for coll_name in COLLECTIONS:
    local_coll = local_db[coll_name]
    atlas_coll = atlas_db[coll_name]

    # Fetch all documents from local collection
    docs = list(local_coll.find({}))

    if docs:
        # Remove _id so Atlas can generate new ones (avoids duplicate key errors)
        for doc in docs:
            doc.pop("_id", None)

        atlas_coll.insert_many(docs)
        print(f"✅ {len(docs)} documents restored into {coll_name}")
    else:
        print(f"⚠️ No documents found in {coll_name}")

print("🎉 Database restore completed successfully.")
