server.py
# server.py — liaison uniquement

from flask import Flask, request, jsonify
from pymongo import MongoClient
from pymongo.errors import OperationFailure
import requests
import traceback

app = Flask(__name__)

client = MongoClient(
    "mongodb://127.0.0.1:27017,"
    "127.0.0.1:27018,"
    "127.0.0.1:27019/"
    "?replicaSet=rs0",
    serverSelectionTimeoutMS=5000,
    connectTimeoutMS=5000,
    socketTimeoutMS=5000
)
admin = client.admin
OPLOG_SIZE_MB = 2048
ACTIONS = {
    0: "Do Nothing",
    1: "Add Secondary Node",
    2: "Remove Secondary Node",
    3: "Increase Oplog Size",
    4: "Decrease Oplog Size",
    5: "Enable ChainingAllowed",
    6: "Disable ChainingAllowed",
    8: "Add Arbiter",
    9: "Remove Arbiter",
}
ARBITER_HOST  = "127.0.0.1:27020"   # ← BUG CORRIGÉ : variable manquante


# ─── Helpers (manquants dans l'original) ──────────────────────────────────────
def get_cfg():
    """
    Retourne la configuration actuelle du Replica Set.
    """
    return admin.command("replSetGetConfig")["config"]
def save_cfg(cfg, validate=True):

    cfg["version"] += 1

    if validate:
        validate_config(cfg)

    return admin.command("replSetReconfig", cfg)

import time
from pymongo.errors import OperationFailure

def wait_stable(timeout=60):
    """
    Attend que le Replica Set soit stable après une reconfiguration.
    Retourne True lorsque tous les membres sont dans un état stable.
    """

    start = time.time()

    while time.time() - start < timeout:

        try:

            status = admin.command("replSetGetStatus")

            stable = True

            for member in status["members"]:

                state = member["stateStr"]

                if state not in (
                    "PRIMARY",
                    "SECONDARY",
                    "ARBITER"
                ):
                    stable = False
                    break

            if stable:
                return True

        except OperationFailure:
            pass

        except Exception:
            pass

        time.sleep(2)

    raise RuntimeError(
        "Replica Set non stabilisé après {} secondes".format(timeout)
    )
def validate_config(cfg):

    members = cfg["members"]

    hosts = set()

    votes = 0

    secondaries = 0

    arbiters = 0

    for m in members:

        if m["host"] in hosts:
            raise ValueError("Host dupliqué")

        hosts.add(m["host"])

        votes += m.get("votes",1)

        if m.get("arbiterOnly",False):
            arbiters += 1
        else:
            secondaries += 1

    if votes < 3:
        raise ValueError("Quorum insuffisant")

    if secondaries < 2:
        raise ValueError("Au moins deux nœuds de données")

    return True
# ─── Actions ──────────────────────────────────────────────────────────────────

def execute_action(action):
    global OPLOG_SIZE_MB
    if action ==0:
       print("DO nothing") 
    elif action == 1:
        cfg = get_cfg()
        used_hosts = {m["host"] for m in cfg["members"]}
        CANDIDATE_HOSTS = [

          "127.0.0.1:27020",

          "127.0.0.1:27021",

          "127.0.0.1:27022"

         ]
        free_hosts = [h for h in CANDIDATE_HOSTS if h not in used_hosts]

        if not free_hosts:
           return {
            "success": False,
            "message": "Aucun candidat disponible"
            }

    # Vérifier que le serveur répond
        try:
             MongoClient(
               f"mongodb://{free_hosts[0]}",
               serverSelectionTimeoutMS=3000
             ).admin.command("ping")

        except Exception:

                 return {
                        "success": False,
                        "message": "Le nouveau noeud n'est pas démarré"
                 }
        next_id = max(m["_id"] for m in cfg["members"]) + 1

        cfg["members"].append({

              "_id": next_id,

              "host": free_hosts[0],

              "priority": 1,

               "votes": 1

        })
        save_cfg(cfg)

        wait_stable()

        return {"success": True}
    elif action == 2:
        status = admin.command("replSetGetStatus")
        secondaries =    [

           m

           for m in status["members"]

           if m["stateStr"] == "SECONDARY"

        ]
        if len(secondaries) <= 2:

            return {

               "success": False,

               "message": "Suppression refusée : minimum 2 secondaries"

            }

        secondary = secondaries[0]

        cfg = get_cfg()

        cfg["members"] = [

             m

             for m in cfg["members"]

             if m["host"] != secondary["name"]
        ]
        save_cfg(cfg)

        wait_stable()
        return {"success": True}

    elif action == 3:
        OPLOG_SIZE_MB += 512
        admin.command({"replSetResizeOplog": 1, "size": OPLOG_SIZE_MB})

    elif action == 4:
        OPLOG_SIZE_MB = max(1024, OPLOG_SIZE_MB - 512)
        admin.command({"replSetResizeOplog": 1, "size": OPLOG_SIZE_MB})

    elif action == 5:

         cfg = get_cfg()

         settings = cfg.setdefault("settings", {})

         if settings.get("chainingAllowed"):

            return {

               "success": True,

               "message": "Déjà activé"
 
            }
  
         cfg = get_cfg()

         cfg.setdefault("settings", {})["chainingAllowed"] = False

         save_cfg(cfg, validate=False)

         wait_stable()

         return {"success": True}
    elif action == 6:

         cfg = get_cfg()

         settings = cfg.setdefault("settings", {})

         if settings.get("chainingAllowed") == False:

            return {

               "success": True,

               "message": "Déjà désactivé"

            }

         cfg = get_cfg()

         cfg.setdefault("settings", {})["chainingAllowed"] = False

         save_cfg(cfg, validate=False)

         wait_stable()

         return {"success": True}
    elif action == 8:

         cfg = get_cfg()

         members = cfg["members"]

    # Déjà présent ?

         if any(

         m.get("arbiterOnly")

         for m in members

         ):

             return {

               "success": False,

               "message": "Arbiter déjà présent"

             }

    # Garder au moins deux noeuds de données

         data_nodes = [

              m

              for m in members

              if not m.get("arbiterOnly", False)

         ]
         if len(data_nodes) < 2:

              return {

                "success": False,

                "message": "Pas assez de noeuds de données"

              }

    # Vérifier que le serveur existe

         try:

                 MongoClient(

                    f"mongodb://{ARBITER_HOST}",

                    serverSelectionTimeoutMS=3000

                 ).admin.command("ping")
         except Exception:

                 return {

                        "success": False,

                        "message": "Arbiter non démarré"
                 }

         new_id = max(

                 m["_id"]

                 for m in members
         ) + 1

         members.append({

                 "_id": new_id,

                 "host": ARBITER_HOST,

                 "arbiterOnly": True,

                 "priority": 0,

                 "votes": 1

         })
         save_cfg(cfg)
         wait_stable()

         return {"success": True}
    elif action == 9:
        cfg = get_cfg()
        arbiters = [m for m in cfg["members"] if m.get("arbiterOnly", False)]

        if not arbiters:
            print("Aucun arbiter à supprimer")
            return {"success": False, "message": "Aucun arbiter trouvé"}

        arbiter_id = arbiters[0]["_id"]
        cfg["members"] = [m for m in cfg["members"] if m["_id"] != arbiter_id]
        save_cfg(cfg)   # ← BUG CORRIGÉ : idem


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def home():
    return "Flask OK"


PROM_URL = "http://127.0.0.1:9090/api/v1/query"

METRICS = [
    # RAM
    "mongodb_ss_wt_cache_maximum_bytes_configured",
    "mongodb_ss_wt_cache_tracked_dirty_bytes_in_the_cache",
    "mongodb_ss_tcmalloc_generic_current_allocated_bytes",
    "mongodb_sys_memory_Cached_kb",
    # CPU
    "mongodb_ss_opcounters",
    "mongodb_ss_globalLock_currentQueue",
    "mongodb_ss_opLatencies_ops",
    "mongodb_sys_cpu_user_ms",
    # Network
    "mongodb_ss_network_bytesIn",
    "mongodb_ss_network_bytesOut",
    "mongodb_ss_network_numRequests",
    # Disk
    "mongodb_ss_wt_block_manager_bytes_read",
    "mongodb_ss_wt_block_manager_bytes_written",
    "mongodb_ss_wt_block_manager_blocks_written",
    "mongodb_ss_wt_block_manager_blocks_read",
    "mongodb_ss_wt_cache_pages_read_into_cache",
    "mongodb_ss_wt_cache_pages_written_from_cache",
    # EtatReplicaSet
    "mongodb_members_state",
    "mongodb_members_health",
    "mongodb_myState",
    # Synchronisation
    "mongodb_members_optimeDurableDate",
    "mongodb_members_optimeDate",
    "mongodb_members_syncSourceId",
    # Oplog
    "mongodb_oplog_stats_storageStats_size",
    "mongodb_ss_oplog_earliestOptime",
    "mongodb_ss_oplog_latestOptime",
    # Replication
    "mongodb_ss_metrics_repl_apply_ops",
    "mongodb_ss_metrics_repl_apply_batchSize",
    "mongodb_ss_metrics_repl_apply_batches_num",
    "mongodb_ss_metrics_repl_apply_batches_totalMillis",
    # Buffer
    "mongodb_ss_metrics_repl_buffer_count",
    "mongodb_ss_metrics_repl_buffer_maxSizeBytes",
    "mongodb_ss_metrics_repl_buffer_sizeBytes",
    # ReplicationNetwork
    "mongodb_ss_metrics_repl_network_getmores_num",
    "mongodb_ss_metrics_repl_network_ops",
    "mongodb_ss_metrics_repl_network_bytes",
    "mongodb_ss_metrics_repl_network_getmores_totalMillis",
]


def query_metric(metric):
    try:
        r = requests.get(PROM_URL, params={"query": metric}, timeout=5)
        data = r.json()
        result = data["data"]["result"]
        print(metric, "=>", result)
        if not result:
            return 0.0
        # ← BUG CORRIGÉ : somme toutes les séries (multi-membres) au lieu de result[0] seulement
        return sum(float(item["value"][1]) for item in result)
    except Exception as e:
        print(f"Erreur sur {metric}: {e}")
        return 0.0


@app.route("/get_state")
def get_state():
    metrics = [query_metric(m) for m in METRICS]
    return jsonify({"metrics": metrics})


@app.route("/apply-action", methods=["POST"])
def apply_action():
    action = None
    try:
        data   = request.get_json()
        action = int(data["action"])

        print("=" * 50)
        print("ACTION =", action)
        print("=" * 50)
        print(f">>> ACTION {action} : {ACTIONS.get(action, '?')}")
        execute_action(action)
        return jsonify({"status": "success", "action": action})

    except Exception as e:
        print(f">>> ERREUR action={action} : {e}")  # ← et ça
        traceback.print_exc()
        return jsonify({"status": "error", "action": action, "message": str(e)}), 500
@app.route("/replica-status")
def replica_status():
    try:
        status    = client.admin.command("replSetGetStatus")
        primary   = 0
        secondary = 0
        arbiter   = 0

        for member in status["members"]:
            state = member["stateStr"]
            if state == "PRIMARY":
                primary += 1
            elif state == "SECONDARY":
                secondary += 1
            elif state == "ARBITER":
                arbiter += 1

        # ← BUG CORRIGÉ : return était DANS la boucle → retournait après le 1er membre
        return jsonify({
            "primary":   primary,
            "secondary": secondary,
            "arbiter":   arbiter,
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
