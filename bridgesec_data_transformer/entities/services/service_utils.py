
def fetch_collection(db, collection_name):
    """
    Fetch all documents from a given collection in the database.
    """
    collection = db[collection_name]
    documents = list(collection.find({}))

    # Remove MongoDB _id
    for doc in documents:
        doc.pop('_id', None)

    return documents
