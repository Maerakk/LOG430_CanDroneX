# CanDroneX — Phase 1 (monolithe modulaire)

Plateforme B2B de commande de services de connectivité 5G pour drones.
Projet LOG430, Automne 2026 — Maëlle Marinier.

## Démarrer

```
docker compose up --build
```

L'application démarre sur http://127.0.0.1:5000, avec MySQL sur le port 3310.
Le catalogue (C2 et Imagerie) est chargé automatiquement.

## Démonstration

Dans un autre terminal : `.\scripts\demo.ps1`

Clés d'API de démonstration : `demo_key_1` (CUST-001), `demo_key_2` (CUST-002).

## Tests

```
pip install -r requirements.txt
python -m pytest tests/unit          # tests unitaires, sans base
docker compose up -d db
python -m pytest tests/integration   # tests d'intégration, avec MySQL
```

## Arrêter et réinitialiser

```
docker compose down       # arrête (les données sont conservées)
docker compose down -v    # arrête et efface la base
```