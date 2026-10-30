# Rapport Phase 2 - contenu par section du gabarit

Mêmes sections et mêmes tableaux que `Gabarit_Rapport_CanDroneX_P2_Microservices.docx`. Figures : `doc/phase2/png/`.

## Page de titre

| Champ | À compléter |
|---|---|
| Équipe / N° d'équipe | Travail individuel |
| Membres (nom, code permanent) | Maëlle MARINIER – MARM83350001 |
| Cours / Groupe | LOG430 — Groupe 01 |
| Session | Automne 2026 |
| Date de remise | |
| Version du document | |

## Documents de référence

Tableau du gabarit inchangé. Divergence signalée : le realm fourni contient `inspectra-demo`, `aerotech-demo` et `candronex-admin`, alors que l'énoncé parle de « inspectra ». J'utilise le realm tel quel, avec `aerotech-demo` comme deuxième client pour tester l'isolation.

## Correspondance Grille d'évaluation → Sections du document

Tableau du gabarit inchangé.

---

# 1. Introduction et objectifs

## 1.1 Le mandat de la Phase 2

La Phase 1 était un monolithe modulaire couvrant UC-02 et UC-04. En Phase 2, ses modules deviennent trois microservices et j'ajoute UC-06. Keycloak et son realm sont fournis : je n'ai créé aucun client ni point `/token`.

- **Frontières** : drone-management-service (UC-02), service-ordering-service (UC-04, catalogue en module séparé), slice-activation-service (UC-06 et inventaire).
- **Données** : une base MySQL par service. Les services se référencent par identifiant. L'IMSI ne sort du service des drones que vers celui des slices.
- **Communication** : REST synchrone avec DTO et délais d'attente. Commandes → Drones, Commandes → Slices, Slices → Drones, sans cycle. L'activation tourne en arrière-plan dans le service des slices.
- **Passerelle** : KrakenD, seul point d'entrée. Les services ne sont pas exposés.
- **Mock réseau** : `MockOpen5GSAdapter` derrière le `NetworkProvisioningPort`, latence de 300 à 1500 ms et taux d'échec configurables.
- **Sécurité** : jeton client credentials, vérifié par la passerelle et par chaque service. Chaque client ne voit que ses données.

Cette version intègre aussi les remarques de l'évaluation de la Phase 1 : contextes ajoutés et cartographie par contexte (3.3), agrégat Service et Service Inventory, ports définis par les commandes, séquence UC-06, délai dépassé distinct de l'échec, codes HTTP et Problem Details corrigés, journal d'audit séparé, contrats OpenAPI, et blocage d'une commande quand le service est déjà actif.

Hors périmètre : autres UC, Kafka, Open5GS, configuration de Keycloak, observabilité, CI/CD, VM et K3S.

## 1.2 Cas d'utilisation couverts

| ID | Cas d'utilisation | Priorité | Portée Phase 2 |
|---|---|---|---|
| UC-02 | Enregistrer un drone et son identité réseau | Must | Repris dans drone-management-service |
| UC-04 | Commander les services de connectivité d'un drone | Must | Repris dans service-ordering-service |
| UC-06 | Activer et configurer une slice | Must | Implémenté dans slice-activation-service avec le mock réseau |
| Autres UC | Hors périmètre de la Phase 2 | — | Aucune implémentation |

**UC-06 – Activer et configurer une slice**

Acteur : CanDroneX, à la suite d'une commande. Préconditions : commande acceptée, drone éligible du client, jeton valide.

Scénario principal :
1. Le service des commandes demande l'activation de chaque élément au service des slices.
2. Le service des slices obtient l'IMSI du drone et crée le Service à l'état PENDING (202).
3. En arrière-plan, le Service passe à ACTIVATING et la configuration est envoyée au réseau.
4. Le réseau confirme : le Service passe à ACTIVE et `activatedAt` est enregistré.
5. À la consultation, la commande reprend l'état des services : COMPLETED si les deux sont actifs.

Scénarios alternatifs :
- **Non authentifié** : jeton absent, expiré ou invalide, réponse 401, rien n'est modifié.
- **Échec** : le réseau refuse, le Service passe à FAILED. La commande est FAILED, ou PARTIALLY_COMPLETED si l'autre service est actif.
- **Délai dépassé** : 3 essais (opération idempotente), puis UNKNOWN. La commande reste IN_PROGRESS.
- **Demande répétée** : le Service existant est renvoyé, sans doublon.
- **Drone inconnu, d'un autre client ou non éligible** : 404 ou 422.

Adaptations de UC-02 et UC-04 : le propriétaire est le client du jeton (`azp`), le rejeu renvoie 200, l'offre est référencée par son identifiant, et la commande déclenche UC-06.

## 1.3 Attributs de qualité prioritaires

| # | Attribut de qualité | Motivation | Vérification |
|---|---|---|---|
| 1 | Sécurité | Chaque client B2B ne voit que ses drones, commandes et services | Tests 401 et d'accès entre clients |
| 2 | Fiabilité | Pas de doublon ni d'état incohérent | Tests de rejeu et d'échec |
| 3 | Performance | P95 d'activation ≤ 5 s et 600 ops/s | Mesures k6 + SQL (10.4) |
| 4 | Modifiabilité | Brancher Open5GS sans toucher au domaine | Port réseau, test d'architecture |

## 1.4 Parties prenantes

| Partie prenante | Attente / besoin | Apport de l'architecture |
|---|---|---|
| Client B2B | Appeler les API avec son jeton et suivre ses drones et commandes | Accès par la passerelle, autorisations vérifiées par chaque service |
| Opérateur du réseau 5G | Recevoir des configurations valides, sans doublon | Port réseau idempotent |
| ISDE | Respect des licences de spectre | Paramètres réseau figés à la commande |
| Transport Canada | Liaison C2 fiable | C2 activé indépendamment de l'Imagerie |
| Équipe de développement | Faire évoluer un service sans casser les autres | Frontières par contexte, tests de contrat |
| Conformité | Savoir quel client a fait quoi | Journal d'audit |

---

# 2. Contraintes d'architecture

## 2.1 Contraintes techniques

| # | Contrainte technique | Description / justification |
|---|---|---|
| 1 | Au moins deux microservices | Trois services, dont un pour les slices |
| 2 | Une base par service | Trois conteneurs MySQL, aucun accès à la base d'un autre |
| 3 | REST synchrone avec DTO | Appels REST entre services, pas de courtier; activation en arrière-plan |
| 4 | Architecture hexagonale | Ports dans le domaine, adaptateurs autour |
| 5 | API Gateway | Seul point d'entrée, services sans port exposé (choix de KrakenD : ADR-003) |
| 6 | Keycloak préconfiguré | Client credentials, audience `candronex-api` |
| 7 | Mock réseau | Adaptateur interne au service des slices |
| 8 | Docker Compose | Tout démarre avec `docker compose up --build` |

## 2.2 Contraintes réglementaires

| # | Loi, règlement ou organisme | Contrainte / impact sur l'architecture |
|---|---|---|
| 1 | Loi sur les télécommunications / CRTC | Accès authentifié, IMSI masqué |
| 2 | LPRPDE / Loi 25 | IMSI copié seulement là où il sert |
| 3 | Transport Canada (RAC partie IX) | C2 actif même si l'Imagerie échoue |
| 4 | ISDE (CNR-SPB-001-23) | Paramètres réseau figés à la commande |

## 2.3 Contraintes organisationnelles et conventions

| # | Élément | Convention retenue |
|---|---|---|
| 1 | Convention d'API | `/api/{api}/v1/{ressource}` et contrats OpenAPI versionnés |
| 2 | Erreurs | `application/problem+json` (RFC 9457) |
| 3 | Code | Python 3.12, Flask, SQLAlchemy; code en anglais, documentation en français |
| 4 | Structure | `domain/` (avec `port/inbound`, `port/outbound`), `application/`, `adapter/inbound`, `adapter/outbound`, `main.py` |

---

# 3. Contexte et périmètre

## 3.1 Contexte métier

Figure 1.

| Élément | Description |
|---|---|
| Client B2B | Application cliente d'un exploitant de drones, identifiée par un JWT obtenu par client credentials. Ses drones et commandes lui appartiennent. |
| Drone | Appareil du client; abonné du réseau identifié par son IMSI |
| Offre | Service du catalogue : C2 / URLLC (contrôle du drone, faible latence) ou Imagerie / eMBB (images, haut débit) |
| Commande | Demande pour un drone, un élément par offre |
| Service | Slice associée à un drone, créée à partir d'un élément |

Dans le scénario bout en bout, le client commande C2 et Imagerie pour le même drone, et chaque service est activé séparément.

## 3.2 Contexte technique

Figure 2.

| Système externe | Interaction avec CanDroneX |
|---|---|
| Keycloak fourni | Émet les jetons JWT pour les clients de démonstration du realm candronex et publie ses clés (JWKS) |
| Client B2B | Obtient son jeton auprès de Keycloak, puis n'appelle que la passerelle |
| Réseau 5G | Simulé par le `MockOpen5GSAdapter`, interne au service des slices |

## 3.3 Cartographie du domaine

Figures 3 (carte des contextes) et 4 (modèle par contexte).

| Élément du domaine | Exemple |
|---|---|
| Contexte délimité | Drone Management, Service Catalog, Service Ordering, Service Activation, Service Inventory, Gestion des clients (Keycloak), Audit |
| Agrégat | Drone; ServiceSpecification; ServiceOrder; Service (Inventory) |
| Entité | Drone, ServiceOrder, ServiceOrderItem, Service, Client, Credential, AuditEntry |
| Objet-valeur | DroneId, Imsi, Iccid; CharacteristicValue; OrderedService, ServiceCharacteristic; NetworkConfiguration, ServiceState |
| Service applicatif | RegisterDrone, PlaceServiceOrder, GetServiceOrder, CatalogQueries, RequestActivation, ActivateService, InventoryQueries |
| Service de domaine | Calcul de l'état global de la commande, construction de la configuration réseau |
| Référence entre contextes | Par identifiant : `droneId`, `serviceId`, `orderItemId` |

Changements depuis le monolithe :
- Fleet devient Drone Management, seul propriétaire de l'IMSI.
- Orders et Catalog restent deux modules dans un même service : le catalogue n'est lu que par les commandes, un service de plus coûterait un appel réseau par commande.
- Activation et Inventory partagent un service parce qu'ils travaillent sur le même agrégat Service.
- Commandes appelle Activation, jamais l'inverse.

---

# 4. Stratégie de solution

## 4.1 Style architectural et frontières de microservices

| Microservice | Responsabilité |
|---|---|
| drone-management-service | UC-02 : drones, identité réseau et éligibilité. Possède la table `drone`. |
| service-ordering-service | UC-04 : commandes, état global, idempotence, et catalogue des offres. Possède les tables des commandes et du catalogue. |
| slice-activation-service | UC-06 : activation des slices et inventaire des services. Possède la table `service`. |

Chaque service possède sa base et ne lit ni n'écrit dans celle d'un autre. Les dépendances ne forment pas de cycle (figure 5).

## 4.2 Communication REST

| Appelant | API sollicitée | Besoin | Route REST |
|---|---|---|---|
| Client B2B via la passerelle | API des drones | Enregistrer un drone | `POST /api/drone-management/v1/drone` |
| Client B2B via la passerelle | API des drones | Consulter les drones du client authentifié | `GET /api/drone-management/v1/drone[/{droneId}]` |
| Client B2B via la passerelle | API du catalogue | Voir les offres | `GET /api/service-catalog/v1/serviceSpecification` |
| Client B2B via la passerelle | API des commandes | Commander les services d'un drone | `POST /api/service-ordering/v1/serviceOrder` |
| Client B2B via la passerelle | API des commandes | Suivre une commande | `GET /api/service-ordering/v1/serviceOrder/{orderId}` |
| Client B2B via la passerelle | API des slices | Consulter l'état d'un service | `GET /api/slice-activation/v1/service/{serviceId}` |
| service-ordering | API des drones | Vérifier que le drone existe et est éligible | `GET /api/drone-management/v1/drone/{droneId}` |
| service-ordering | API des slices | Demander l'activation d'un élément | `POST /api/slice-activation/v1/service` (interne) |
| service-ordering | API des slices | Lire l'état des services d'une commande | `GET /api/slice-activation/v1/service?orderId=` |
| slice-activation | API des drones | Obtenir l'IMSI du drone | `GET /api/drone-management/v1/drone/{droneId}/networkIdentity` (interne) |

Les demandes et réponses sont en JSON, les erreurs en Problem Details. Délais : connexion 1 s, lecture 1,5 à 2 s, passerelle 5 s. Un service qui ne répond pas donne 503. Si le service des drones est indisponible, la commande est refusée. Si c'est celui des slices, la commande est gardée et l'activation redemandée à la consultation suivante. L'idempotence est décrite en 8.2.

Chaque appel sortant passe par un port défini par le domaine (`DroneDirectory`, `ServiceActivation`, `DroneIdentityProvider`), implémenté par un adaptateur HTTP. Le domaine ne sait pas qu'il parle à un autre service.

## 4.3 Contrats REST et OpenAPI

| Méthode | Chemin | Intention |
|---|---|---|
| POST | `/api/drone-management/v1/drone` | Enregistrer un drone (201, rejeu 200) |
| GET | `/api/drone-management/v1/drone[/{droneId}]` | Consulter ses drones |
| GET | `/api/service-catalog/v1/serviceSpecification` | Lister les offres |
| POST | `/api/service-ordering/v1/serviceOrder` | Créer une commande (201, rejeu 200) |
| GET | `/api/service-ordering/v1/serviceOrder/{orderId}` | Suivre une commande |
| GET | `/api/slice-activation/v1/service[/{serviceId}]` | Consulter l'état des services |

Contrats complets en annexe A. Swagger UI : http://localhost:8082. Le contrat de la passerelle déclare `oauth2` avec le flux `clientCredentials` et l'URL de jeton de Keycloak.

## 4.4 API Gateway et circulation du jeton

KrakenD 2.7 est configuré dans `gateway/krakend.json`.

| Composant | Responsabilité dans le flux |
|---|---|
| API Gateway | Route les appels, gère le CORS, vérifie le jeton et le transmet sans le modifier avec `X-Correlation-Id`. Un nginx interne répond 503/504 en Problem Details si un service est indisponible. |
| Microservices | Revérifient le jeton (signature, `exp`, `iss`, audience `candronex-api`), prennent le client dans la claim `azp` et filtrent les données |
| Keycloak fourni | Émet les jetons (5 min) pour les clients de démonstration |

---

# 5. Vue des blocs de construction — 4+1 : Logique et Développement

Tableau des vues 4+1 du gabarit inchangé.

## 5.1 Décomposition en microservices — vue Logique

Figure 5 : services, contextes, API, base de chaque service et appels entre services.

## 5.2 Structure interne d'un service — architecture hexagonale

Figures 6 (service des slices) et 7 (commandes et drones). Chaque service suit la variante hexagonale vue en cours, avec `inbound` et `outbound` au lieu de `in` et `out` (mot réservé en Python) :
- `domain/port/inbound` : cas d'utilisation (`RegisterDroneUseCase`, `PlaceServiceOrderUseCase`, `RequestActivationUseCase`...), implémentés dans `application/`;
- `domain/port/outbound` : dépôts, autres services et réseau (`DroneRepository`, `DroneDirectory`, `ServiceActivation`, `NetworkProvisioningPort`...);
- `adapter/inbound` : REST; `adapter/outbound` : MySQL, HTTP et mock.

`NetworkProvisioningPort.apply()` est idempotent par `serviceId` et lève `ProvisioningRejected` ou `ProvisioningTimeout`. La configuration utilise les termes du domaine, pas ceux d'Open5GS. En Phase 3, seul `main.py` change pour brancher l'adaptateur réel.

## 5.3 Organisation du code — vue Développement

Figure 8. Un dossier par service avec son code, son `Dockerfile`, son `openapi.yaml`, ses scripts SQL et ses tests. `common/` est le châssis de microservice vu en cours (JWT, journaux, erreurs, client HTTP), sans domaine. `tests/contract/test_architecture.py` vérifie que le domaine n'importe aucun framework et qu'aucun service n'importe le code d'un autre.

---

# 6. Vue d'exécution — 4+1 : Processus

## 6.1 Scénarios de référence

- Figure 9 : obtention du jeton auprès de Keycloak, puis UC-02 par la passerelle, avec le refus sans jeton valide.
- Figure 10 : UC-04 puis UC-06 (commande C2 et Imagerie, appel au mock, services ACTIVE ou FAILED), avec le refus pour le drone d'un autre client.

Capture de `python scripts/demo.py` : drone 201, rejeu 200, sans jeton 401, IMSI invalide 422, champ manquant 400, commande 201, rejeu 200, drone d'un autre client 404, services ACTIVE, commande COMPLETED, accès entre clients 404. Avec `--failure`, la commande et les services finissent en FAILED.

## 6.2 Cycle de vie d'une commande et d'une activation

Figure 11. États d'un Service, repris par l'élément de commande :
- **PENDING** : en attente d'activation;
- **ACTIVATING** : configuration en cours;
- **ACTIVE** : confirmé par le réseau, `activatedAt` enregistré;
- **FAILED** : refus du réseau ou erreur interne;
- **UNKNOWN** : pas de réponse après 3 essais.

État global de la commande, calculé à partir des éléments : ACKNOWLEDGED si tous sont PENDING, IN_PROGRESS si au moins un est PENDING, ACTIVATING ou UNKNOWN, COMPLETED si tous sont ACTIVE, PARTIALLY_COMPLETED si au moins un est ACTIVE et les autres FAILED, FAILED sinon.

`acceptedAt` est fixé à l'acceptation de la commande, `activatedAt` au passage à ACTIVE. Chaque élément est activé séparément, ce qui permet un résultat partiel. Les répétitions sont traitées en 8.2.

---

# 7. Vue de déploiement — 4+1

## 7.1 Topologie de déploiement

Figure 12. Ports exposés : passerelle 8080, Keycloak 8081, Swagger UI 8082. Les trois services (gunicorn, 8 processus, 12 pour les slices) et leurs trois bases MySQL restent sur le réseau Docker, chaque base avec son volume. Variables principales : `DATABASE_URL`, `JWT_ISSUER`, `JWT_AUDIENCE`, URL des autres services, `MOCK_*`. Les secrets sont dans `.env`.

## 7.2 Démarrage et données de démonstration

```
cp .env.example .env   (remplir les secrets)
docker compose up --build
python scripts/demo.py
docker compose down -v (remise à zéro)
```

Le realm Keycloak est importé au démarrage, sans configuration manuelle. Chaque base crée son schéma et ses données de démonstration (catalogue, un drone par client de démonstration). Jeton : `POST http://localhost:8081/realms/candronex/protocol/openid-connect/token` (commande complète dans le README).

---

# 8. Concepts transversaux

## 8.1 Persistance et intégrité des données

Une base par service, créée au démarrage par `db/01_schema.sql` et `db/02_demo_data.sql`. Pas de clé étrangère entre bases : les liens passent par des identifiants. Les caractéristiques du catalogue sont copiées dans la commande, puis dans le Service. Une commande et ses éléments sont écrits dans une seule transaction.

## 8.2 Idempotence des commandes et des activations

- **Commande** : en-tête `Idempotency-Key` obligatoire, contrainte `UNIQUE (client_id, idempotency_key)`. Même demande : 200 avec la même commande. Demande différente : 409.
- **Association slice ↔ drone** : `UNIQUE (order_item_id)`, le Service existant est renvoyé.
- **Configuration réseau** : le passage PENDING → ACTIVATING est un `UPDATE ... WHERE state = 'PENDING'`, donc un seul thread configure, et `apply` est idempotent.
- **Même service commandé deux fois** : un service PENDING, ACTIVATING, ACTIVE ou UNKNOWN bloque une nouvelle commande (409).

La clé et les contraintes sont persistées en base, donc le rejeu fonctionne même après un redémarrage.

## 8.3 Gestion des erreurs et des défaillances

Format commun Problem Details : `type`, `title`, `status`, `detail`, `instance`, `correlationId`. Codes : 400 requête mal formée, 401 jeton invalide, 404 ressource inexistante ou d'un autre client, 409 conflit, 422 règle métier, 500 erreur inattendue, 503 service indisponible, 504 service trop lent.

Une erreur 4xx ne modifie aucune donnée. Les appels entre services ont des délais courts (4.2). Un refus du réseau donne FAILED, une absence de réponse donne UNKNOWN, sans état incohérent.

## 8.4 Versionnement et qualité des contrats OpenAPI

Version dans le chemin (`/v1/`). Un contrat par service avec schémas, exemples, codes et erreurs, et un contrat de passerelle généré avec la sécurité OAuth2. Des tests vérifient que les contrats correspondent aux routes du code et que toutes leurs références se résolvent.

## 8.5 Sécurité B2B

Le client obtient un jeton en client credentials auprès du realm `candronex`. La passerelle transmet `Authorization: Bearer` sans le modifier. Chaque service vérifie la signature, l'expiration, l'émetteur et l'audience, puis identifie le client par la claim `azp`. Les données d'un autre client donnent 404, sans rien divulguer. Les secrets sont dans `.env`, hors du dépôt, et l'IMSI est masqué dans les réponses et les journaux.

## 8.6 Journalisation et corrélation

Chaque service écrit une ligne JSON par événement, avec l'horodatage, le nom du service, l'`orderId`, le `correlationId` et le client. Événements : commande reçue, demande d'activation, appel au port réseau, résultat de l'activation, erreurs. Un journal `audit` séparé trace les actions métier par client. Pour suivre une commande : `docker compose logs | grep <orderId>`.

---

# 9. Décisions d'architecture — ADR

## ADR-001 : Trois microservices et propriété des données

| Champ | Contenu |
|---|---|
| Statut | Accepté |
| Contexte | Le moins de services possible, une base par service, pas de cycle. IMSI sensible. Catalogue lu seulement par les commandes. |
| Décision | drone-management, service-ordering (avec le catalogue), slice-activation. Une base MySQL chacun, références par identifiant. |
| Conséquences | IMSI confiné, pas de cycle. En contrepartie : copies de données, trois bases, plusieurs appels REST par commande. |
| Option écartée | Catalogue en service séparé (un appel de plus par commande). Base partagée (séparation par convention seulement). |

## ADR-002 : Réseau derrière un port, avec un mock

| Champ | Contenu |
|---|---|
| Statut | Accepté |
| Contexte | Pas de cœur 5G en Phase 2, Open5GS en Phase 3. Latence et échecs réalistes. Un délai dépassé n'est pas un échec certain. |
| Décision | `NetworkProvisioningPort` idempotent, avec `ProvisioningRejected` et `ProvisioningTimeout`. Mock configurable. Activation en arrière-plan, 3 essais, puis UNKNOWN. |
| Conséquences | Seul `main.py` change en Phase 3. File d'activation en mémoire, perdue si le conteneur s'arrête. |
| Option écartée | Activation pendant la requête (réponse lente). Courtier de messages (interdit en Phase 2). |

## ADR-003 : KrakenD et jeton vérifié par chaque service

| Champ | Contenu |
|---|---|
| Statut | Accepté |
| Contexte | Passerelle obligatoire, jeton transmis tel quel, chaque service doit le vérifier, erreur uniforme si un service est indisponible. Keycloak fourni. |
| Décision | KrakenD (cours et projet de démarrage). Chaque service revérifie le jeton. Un nginx interne renvoie 503/504 en Problem Details. |
| Conséquences | Un appel qui contourne la passerelle est refusé. Coût : une vérification et un saut réseau de plus. |
| Option écartée | Identité passée dans `X-Client-Id` (falsifiable). Réponse « static » de KrakenD (statut 200 sur une erreur). |

## ADR-004 : Communication entre services et défaillances

| Champ | Contenu |
|---|---|
| Statut | Accepté |
| Contexte | REST synchrone imposé. Une panne ne doit ni bloquer ni corrompre. Activation ne doit pas rappeler Commandes. |
| Décision | Délais courts, 503 sur indisponibilité, pas de réessai automatique, idempotence à chaque étape. Commandes relit l'inventaire à la consultation. |
| Conséquences | Pas de corruption en cas de panne. L'état d'une commande peut avoir du retard jusqu'à la consultation suivante. |
| Option écartée | Rappel d'Activation vers Commandes (cycle). Interrogation périodique (charge inutile). |

---

# 10. Exigences de qualité

## 10.1 Attributs de qualité prioritaires

| Attribut de qualité | Motivation | Vérification |
|---|---|---|
| Sécurité | Limiter l'accès de chaque client B2B à ses ressources | Validation JWT par service, tests 401 et d'accès entre clients |
| Fiabilité | Pas de doublon ni d'état incohérent | Idempotence (8.2), tests de rejeu et d'échec |
| Performance | P95 ≤ 5 s, 600 ops/s | Mesures k6 + SQL (10.4) |
| Modifiabilité | Brancher Open5GS sans toucher au domaine | Port réseau, test d'architecture |

## 10.2 Scénarios de qualité

| ID | Stimulus | Réponse attendue | Vérification |
|---|---|---|---|
| Q1 | Un appel arrive sans jeton Bearer valide | Le microservice refuse l'appel sans modifier les données | Test d'intégration : 401 |
| Q2 | Un client lit les données d'un autre | 404, rien divulgué | Tests et démo |
| Q3 | Service des drones arrêté pendant une commande | 503, aucune commande créée | Test d'intégration |
| Q4 | Le réseau refuse toutes les activations | Services et commande en FAILED | Test, `demo.py --failure` |
| Q5 | Le réseau ne répond pas | 3 essais puis UNKNOWN | Test, `MOCK_TIMEOUT_RATE=1` |
| Q6 | Même commande rejouée | 200, aucun doublon | Test d'intégration |

## 10.3 Stratégie et résultats des tests

`python -m pytest` lance 110 tests, sans base ni Keycloak : tests unitaires de UC-02, UC-04 et UC-06 (32, 32 et 17), 8 tests d'intégration où les trois services s'appellent en HTTP avec le mock, et 21 tests de contrat et d'architecture. Limite : les dépôts SQL ne sont pas testés contre MySQL, ils le sont par la démo et les mesures.

| Exigence | Résultat attendu | Résultat constaté |
|---|---|---|
| Tests automatisés | Tous les tests requis réussissent | 110/110 |
| Accès B2B | 401 sans jeton valide; accès interclient refusé | 8 cas de 401, 404 entre clients sur drone, commande et service |
| Activation | Succès et échec du mock sont couverts | ACTIVE, FAILED et UNKNOWN vérifiés |
| Idempotence | Aucun doublon sur rejeu | 1 commande, 2 services, 2 configurations après rejeu |

## 10.4 Mesures de performance

Protocole (`python load-tests/run_measurement.py`) : pile remise à zéro, mock par défaut, 300 000 drones préchargés (un drone neuf par commande). k6 par la passerelle avec un taux d'arrivée constant, mélange 60 % consultations, 30 % commandes, 10 % drones. File d'activation relevée toutes les 5 s. P95 calculé en SQL sur tous les éléments commandés, ceux non actifs comptant comme > 5 s.

| Mesure | Cible | Résultat et analyse |
|---|---|---|
| Délai d'activation P95 | ≤ 5 s | **3,39 s, atteint.** 46 026 éléments commandés, tous ACTIVE sauf 546 jamais reçus par le service des slices (comptés > 5 s), 0 FAILED. |
| Débit soutenu | ≥ 600 opérations/s | **Non atteint** : 536 ops/s, 2 529 itérations abandonnées, 28 % d'erreurs (504 sur les commandes). |
| Protocole | 1 min + 5 min | k6 0.54, i9-12900H, 32 Go, Docker Desktop (20 vCPU), mock 300 à 1500 ms et 0 % d'échec |
| File d'activation | Pas de croissance continue | Stable, entre 21 et 265 services en attente |

Ces chiffres viennent de la mesure sur le code livré (`results/measurement-full-4-code-livre.json`). Elle a été précédée de trois campagnes de réglage : 4 processus par service donnaient 484 ops/s et 35 % d'erreurs, 8 processus avec les pools MySQL ajustés 536 ops/s et 28 %, et nginx avec connexions persistantes et 12 processus pour les slices n'a plus rien amélioré.

L'écart s'explique par la machine, presque saturée (16 à 17 vCPU sur 20, avec k6 et les bases sur le même poste), et par le coût d'une commande : 6 vérifications de jeton, 6 appels HTTP et environ 8 requêtes SQL. Les commandes en 504 sont quand même créées, et un réessai avec la même clé les retrouve sans doublon.

Pistes : une seule demande d'activation par commande, éviter la double vérification du jeton en interne, un serveur asynchrone, des événements en Phase 3, et une mesure sur des machines séparées.

---

# 11. Risques et dette technique

| Risque / dette | Impact | Mitigation |
|---|---|---|
| Dépendance synchrone Commandes → Drones | Pas de commande si le service des drones tombe | Délai court et 503; copie locale par événements en Phase 3 |
| File d'activation en mémoire | Services PENDING après un arrêt brutal | Courtier en Phase 3 |
| Services UNKNOWN | Restent UNKNOWN sans vérification du réseau | Réconciliation (UC-13) en Phase 3 |
| Deux commandes simultanées pour le même service et le même drone | Peuvent passer toutes les deux | Contrainte d'unicité sur les services actifs |
| Débit non tenu | 504 sur des commandes pourtant créées | Pistes en 10.4 |
| Dérive des contrats | Un service casse ses appelants | Tests de contrat |

---

# 12. Glossaire

## 12.1 Langage métier

| Terme | Définition |
|---|---|
| Slice | Service de connectivité reposant sur une tranche logique du réseau 5G |
| Client B2B | Exploitant de drones dont l'application s'authentifie par client credentials |
| Drone | Appareil du client; abonné du réseau identifié par son IMSI |
| Commande | Demande d'un client pour un drone, un élément par offre |
| Service de connectivité | Offre du catalogue (C2 / URLLC, Imagerie / eMBB); une fois commandée, Service associé au drone |
| Activation | Application de la configuration d'un Service au réseau 5G |
| Délai dépassé | Pas de réponse du réseau, résultat inconnu (UNKNOWN) |
| Clé d'idempotence | Valeur du client qui empêche les doublons de commande |
| acceptedAt / activatedAt | Acceptation de la commande / passage du Service à ACTIVE |

## 12.2 Acronymes

| Acronyme | Signification |
|---|---|
| IMSI | International Mobile Subscriber Identity |
| JWT | JSON Web Token |
| CORS | Cross-Origin Resource Sharing |
| DTO | Data Transfer Object |
| P95 | 95e centile |
| eMBB | enhanced Mobile Broadband |
| URLLC | Ultra-Reliable Low-Latency Communications |
| S-NSSAI | Single Network Slice Selection Assistance Information |
| JWKS | JSON Web Key Set |
| ISDE | Innovation, Sciences et Développement économique Canada |
| TMF | TM Forum |

---

# Annexes

## Annexe A — Contrats OpenAPI

Contrats : `gateway/openapi.yaml` (passerelle, OAuth2 clientCredentials), `services/drone-management-service/openapi.yaml`, `services/service-ordering-service/openapi.yaml`, `services/slice-activation-service/openapi.yaml`, tous en version 1.0.0 et visibles dans Swagger UI (http://localhost:8082).

| Opération OpenAPI | UC | Tests |
|---|---|---|
| registerDrone, listDrones, getDrone | UC-02 | Tests REST du service des drones, intégration |
| getNetworkIdentity (interne) | UC-06 | `test_network_identity_is_only_given_to_the_owner` |
| placeServiceOrder, getServiceOrder | UC-04 | Tests REST du service des commandes, intégration |
| listServiceSpecifications | UC-04 | `test_rest_catalog_lists_offers_by_id` |
| requestServiceActivation (interne), searchServices, getService | UC-06 | Tests REST du service des slices, intégration |
| Toutes | | `tests/contract/test_contracts.py` |

## Annexe B — Persistance

Figure 13.
- **drone-db** : table `drone`, contraintes `uq_drone_per_client`, `uq_imsi`, `uq_iccid`.
- **ordering-db** : tables du catalogue et `service_order`, `service_order_item`, contraintes `uq_idempotency_per_client`, `uq_specification_per_order`.
- **activation-db** : table `service`, contrainte `uq_service_per_order_item`.
- Initialisation par `services/<service>/db/`, données de démonstration incluses, remise à zéro par `docker compose down -v`. Aucune clé étrangère entre bases.

## Annexe C — Conteneurisation et exécution

- Démarrer et arrêter : `docker compose up --build`, `docker compose down` (ou `down -v` pour remettre à zéro).
- Jeton et appel de la passerelle : voir le README.
- Journaux : `docker compose logs | grep <orderId>`.
- Tests : `python -m pytest`. UC-06 : `python scripts/demo.py`. Mesures : `python load-tests/run_measurement.py`.

## Annexe D — Auto-évaluation

| # | Critère d'évaluation Phase 2 | Auto-évaluation | Éléments justificatifs | Écarts / limites |
|---|---|---|---|---|
| 1 | Analyse du domaine et UC-06 | Atteint | 1.2, 3.3, figures 3 et 4 | |
| 2 | Architecture microservices | Atteint | 4.1, 4.2, ADR-001 | Catalogue regroupé avec les commandes |
| 3 | API Gateway et sécurité B2B | Atteint | 4.4, 8.5, ADR-003 | 401 de KrakenD sans corps |
| 4 | Architecture hexagonale et API | Atteint | 5.2, 4.3, test d'architecture | |
| 5 | UC-06 et réseau simulé | Atteint | 1.2, 5.2, 8.2, ADR-002 | File d'activation en mémoire |
| 6 | Documentation et ADR | Atteint | Sections 1 à 12, 4 ADR | |
| 7 | Mesure de la performance | Partiel | 10.4, `results/` | Débit 536 ops/s au lieu de 600 |
| 8 | Tests | Atteint | 10.3, 110 tests | Dépôts SQL non testés contre MySQL |
| 9 | Conteneurisation, logs et livraison | Atteint | 7, 8.6, README | |

## Annexe E — Déclaration sur l'IA

À compléter.
