# Projet-fin-d-etude-master-IAA
Voici une description professionnelle en français que vous pouvez utiliser dans votre dépôt **GitHub**.

---

# Optimisation dynamique d'un MongoDB Replica Set à l'aide de LSTM et PPO

Ce projet propose une approche intelligente pour l'optimisation dynamique d'un **MongoDB Replica Set** en utilisant une combinaison de **Deep Learning (LSTM)** et **Reinforcement Learning (Proximal Policy Optimization - PPO)**.

L'objectif est de réduire automatiquement la charge du système en sélectionnant les meilleures actions de reconfiguration du Replica Set selon son état courant.

## Fonctionnement

L'architecture développée repose sur plusieurs composants :

* **MongoDB Replica Set** servant d'infrastructure distribuée.
* **MongoDB Exporter** pour la collecte des métriques système.
* **Prometheus** pour l'exposition et le stockage des métriques.
* **Grafana** pour la visualisation en temps réel.
* **Flask API** assurant la communication entre l'agent intelligent et MongoDB.
* **LSTM** pour la prédiction de la charge future à partir des métriques collectées.
* **PPO** pour apprendre automatiquement la meilleure stratégie de reconfiguration.

Le LSTM estime la charge future du système tandis que l'agent PPO décide des actions à appliquer afin de maintenir de bonnes performances et une haute disponibilité.

## Actions prises en charge

L'agent peut exécuter plusieurs opérations sur le Replica Set :

* Ne rien faire
* Ajouter un nœud secondaire
* Supprimer un nœud secondaire
* Augmenter la taille de l'Oplog
* Diminuer la taille de l'Oplog
* Activer ou désactiver *ChainingAllowed*
* Effectuer un *StepDown* du Primary
* Ajouter un Arbiter
* Supprimer un Arbiter

Une **Safety Layer** empêche l'exécution des actions pouvant compromettre la disponibilité du Replica Set.

## Technologies utilisées

* Python
* MongoDB Replica Set
* Flask
* MongoDB Exporter
* Prometheus
* Grafana
* TensorFlow / Keras (LSTM)
* Stable-Baselines3 (PPO)
* Gymnasium
* NumPy
* Requests

## Résultats

Le modèle LSTM obtient de bonnes performances de prédiction avec :

* **MSE :** 0.0047
* **MAE :** 0.0403
* **RMSE :** 0.0686
* **R² :** 0.8694

L'agent PPO apprend progressivement une politique permettant de sélectionner les actions de reconfiguration les plus adaptées afin d'optimiser dynamiquement le Replica Set.

## Contributions

Ce projet met en œuvre :

* un environnement Gym personnalisé connecté à un **Replica Set MongoDB réel** ;
* une API Flask permettant l'interaction entre PPO et MongoDB ;
* un système de collecte des métriques basé sur Prometheus ;
* une prédiction de charge par réseau de neurones LSTM ;
* une optimisation dynamique du Replica Set par apprentissage par renforcement.

