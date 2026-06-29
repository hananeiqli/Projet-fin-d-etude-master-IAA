
import json
import random
import threading
import time

from pymongo import MongoClient

# ==================================================
# MongoDB Replica Set
# ==================================================

client = MongoClient(
    "mongodb://127.0.0.1:27017/?replicaSet=rs0"
)

db = client.ppo_workload

movies_col = db.movies
products_col = db.products

# ==================================================
# Chargement datasets locaux
# ==================================================

with open(
    "datasets/movies.json",
    "r",
    encoding="utf-8"
) as f:
    movies_dataset = json.load(f)

with open(
    "datasets/products.json",
    "r",
    encoding="utf-8"
) as f:
    products_dataset = json.load(f)

print("Movies:", len(movies_dataset))
print("Products:", len(products_dataset))

# ==================================================
# Index
# ==================================================

movies_col.create_index("title")
products_col.create_index("name")

# ==================================================
# INSERT MOVIES
# ==================================================

def movie_writer():

    while True:

        docs = []

        for _ in range(100):

            doc = random.choice(
                movies_dataset
            ).copy()

            doc["ts"] = time.time()

            docs.append(doc)

        try:

            movies_col.insert_many(
                docs,
                ordered=False
            )

        except:
            pass

# ==================================================
# INSERT PRODUCTS
# ==================================================

def product_writer():

    while True:

        docs = []

        for _ in range(100):

            doc = random.choice(
                products_dataset
            ).copy()

            doc["ts"] = time.time()

            docs.append(doc)

        try:

            products_col.insert_many(
                docs,
                ordered=False
            )

        except:
            pass

# ==================================================
# READ MOVIES
# ==================================================

def movie_reader():

    while True:

        try:

            keyword = random.choice(
                movies_dataset
            )["title"]

            list(
                movies_col.find(
                    {"title": keyword}
                ).limit(50)
            )

        except:
            pass

# ==================================================
# READ PRODUCTS
# ==================================================

def product_reader():

    while True:

        try:

            keyword = random.choice(
                products_dataset
            )["name"]

            list(
                products_col.find(
                    {"name": keyword}
                ).limit(50)
            )

        except:
            pass

# ==================================================
# THREADS
# ==================================================

threads = [

    threading.Thread(
        target=movie_writer,
        daemon=True
    ),

    threading.Thread(
        target=product_writer,
        daemon=True
    ),

    threading.Thread(
        target=movie_reader,
        daemon=True
    ),

    threading.Thread(
        target=movie_reader,
        daemon=True
    ),

    threading.Thread(
        target=product_reader,
        daemon=True
    ),

    threading.Thread(
        target=product_reader,
        daemon=True
    )
]

for t in threads:
    t.start()

print("Workload started")

# ==================================================
# Monitoring
# ==================================================

while True:

    movies_count = movies_col.count_documents({})
    products_count = products_col.count_documents({})

    print(
        f"Movies={movies_count} | "
        f"Products={products_count} | "
        f"Total={movies_count + products_count}"
    )

    time.sleep(20)
