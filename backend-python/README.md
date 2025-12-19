# Close Rocket API

API REST pour récupérer des simulations de trajectoires de fusées depuis Supabase et effectuer des prédictions ML.

## 🚀 Démarrage Rapide

### 1. Installation des dépendances

```bash
pip install -r requirements.txt
```

### 2. Configuration

Assurez-vous que le fichier `.env` contient vos credentials Supabase :

```env
SUPABASE_URL=https://pxddpdmnlmirghrvgewb.supabase.co
SUPABASE_KEY=votre_clé_supabase
```

### 3. Lancement de l'API

```bash
uvicorn main:app --reload
```

L'API sera disponible sur `http://localhost:8000`

### 4. Documentation interactive

Une fois l'API lancée, accédez à :
- **Swagger UI** : http://localhost:8000/docs
- **ReDoc** : http://localhost:8000/redoc

## 📚 Endpoints

### `GET /`
Endpoint racine pour vérifier l'état de l'API.

**Exemple :**
```bash
curl http://localhost:8000/
```

**Réponse :**
```json
{
  "message": "Close Rocket API v2.0",
  "status": "operational",
  "endpoints": {
    "simulations": "/simulations?ids=rocket_0000,rocket_0001",
    "predict": "/predict (POST)"
  }
}
```

---

### `GET /simulations`
Récupère une ou plusieurs simulations complètes.

**Paramètres :**
- `ids` (query parameter) : IDs de fusées séparés par virgule (ex: `rocket_0000,rocket_0001`)

**Exemple avec 1 simulation :**
```bash
curl "http://localhost:8000/simulations?ids=rocket_0000"
```

**Exemple avec plusieurs simulations :**
```bash
curl "http://localhost:8000/simulations?ids=rocket_0000,rocket_0001,rocket_0002"
```

**Réponse :**
```json
{
  "count": 1,
  "simulations": [
    {
      "rocket_id": "rocket_0000",
      "rocket_parameters": {
        "rocket_id": "rocket_0000",
        "delay": 0.0,
        "heading": 25.62,
        "ramp_inclinaison": 86.86,
        "motor_name": "Pro75M1670",
        "radius": 0.133,
        "mass": 8.29,
        "inertia": "(9.7, 9.7, 0.009)",
        ...
      },
      "trajectory": [
        {
          "time": 0.0,
          "x": 0.0,
          "y": 0.0,
          "z": 459.01,
          "wind_velocity_x": -0.377,
          "wind_velocity_y": -4.384
        },
        ...
      ],
      "metadata": {
        "total_points": 1523,
        "duration": 45.23,
        "max_altitude": 1234.56,
        "landing_position": {
          "x": 123.45,
          "y": 678.90
        }
      }
    }
  ]
}
```

**Codes de réponse :**
- `200` : Succès
- `400` : Format d'ID invalide (doit être `rocket_XXXX`)
- `404` : Un ou plusieurs IDs n'existent pas
- `500` : Erreur de connexion base de données

---

### `POST /predict`
Accepte les paramètres de fusée pour prédiction ML.

**Corps de la requête :**
```json
{
  "delay": 0.0,
  "heading": 25.62,
  "ramp_inclinaison": 86.86,
  "motor_name": "Pro75M1670",
  "radius": 0.133,
  "mass": 8.29,
  "inertia": "(9.7, 9.7, 0.009)",
  "center_of_mass_without_motor": 2.14,
  "cone_length": 0.41,
  "rocket_length": 2.96,
  "fin_cat": "trapezoidal",
  "number_of_ailerons": 4,
  "root_chord": 0.25,
  "tip_chord": 0.18,
  "span": 0.23,
  "fins_pos": 0.09,
  "fin_inclinaison": 0.0,
  "drag_coeff": 1.07,
  "trigger": "apogee"
}
```

**Exemple :**
```bash
curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -d @predict_request.json
```

**Réponse :**
```json
{
  "status": "success",
  "message": "Paramètres de fusée reçus et validés. Modèle ML non encore implémenté.",
  "request_id": null
}
```

**Codes de réponse :**
- `200` : Succès
- `422` : Erreur de validation (paramètres invalides)

**Validations :**
- `radius`, `mass`, `cone_length`, `rocket_length`, `root_chord`, `tip_chord`, `span`, `drag_coeff` : doivent être > 0
- `heading`, `ramp_inclinaison` : doivent être entre 0 et 360°
- `number_of_ailerons` : doit être entre 0 et 8
- `fin_cat` : doit être `trapezoidal` ou `elyptique`
- `trigger` : doit être `apogee`

---

## 🧪 Tests

Un script de test complet est disponible : `test_api.py`

**Lancer les tests :**

1. Démarrez l'API dans un terminal :
```bash
uvicorn main:app --reload
```

2. Dans un autre terminal, lancez les tests :
```bash
python test_api.py
```

Le script teste :
- ✅ Endpoint racine
- ✅ Récupération d'une simulation
- ✅ Récupération de plusieurs simulations
- ✅ Format d'ID invalide (erreur attendue)
- ✅ ID inexistant (erreur attendue)
- ✅ Prédiction valide
- ✅ Validation des paramètres (erreurs attendues)

---

## 📁 Structure du Projet

```
backend-python/
├── main.py                 # Application FastAPI (endpoints)
├── database.py             # Client Supabase (requêtes DB)
├── requirements.txt        # Dépendances Python
├── test_api.py             # Script de test
├── README.md               # Documentation
├── .env                    # Credentials Supabase (ne pas commit)
├── database-manager.py     # Script de migration (ancien)
└── DatasetGenerator/       # Génération de dataset
```

---

## 🗄️ Schéma Base de Données

### Table `rockets`
Contient les paramètres des 1000 fusées (rocket_0000 à rocket_0999).

**Colonnes :**
- `rocket_id` (TEXT, PK)
- 20 paramètres : `delay`, `heading`, `motor_name`, `radius`, `mass`, etc.

### Table `trajectories`
Points de trajectoire (x, y, z) pour chaque fusée.

**Colonnes :**
- `id` (BIGSERIAL, PK)
- `rocket_id` (TEXT, FK)
- `time`, `x`, `y`, `z` (FLOAT)

### Table `wind_conditions`
Conditions de vent pour chaque point temporel.

**Colonnes :**
- `id` (BIGSERIAL, PK)
- `rocket_id` (TEXT, FK)
- `time`, `wind_velocity_x`, `wind_velocity_y` (FLOAT)

---

## 🔧 Développement

### Modifier l'API

1. **Ajouter un endpoint** : Éditer `main.py`, ajouter une fonction décorée avec `@app.get()` ou `@app.post()`
2. **Modifier la logique DB** : Éditer `database.py`, ajouter des méthodes à la classe `SupabaseDatabase`
3. **Ajouter des validations** : Utiliser les `field_validator` de Pydantic dans les modèles

### Lancer en mode développement

```bash
uvicorn main:app --reload --port 8000
```

Le flag `--reload` recharge automatiquement l'API à chaque modification de code.

---

## 🚨 Gestion des Erreurs

L'API retourne des erreurs structurées :

**400 Bad Request :**
```json
{
  "error": "Invalid rocket_id format: 'rocket_abc'. Expected format: rocket_XXXX"
}
```

**404 Not Found :**
```json
{
  "error": "Rocket rocket_9999 not found in database"
}
```

**422 Unprocessable Entity :**
```json
{
  "detail": [
    {
      "type": "greater_than",
      "loc": ["body", "radius"],
      "msg": "Input should be greater than 0"
    }
  ]
}
```

**500 Internal Server Error :**
```json
{
  "error": "Database connection error occurred"
}
```

---

## 📝 Notes

- **CORS** : Configuré pour `http://localhost:3000` (frontend Next.js)
- **Logging** : Logs INFO dans la console
- **ML Model** : L'endpoint `/predict` est une structure vide pour future intégration
- **Performance** : Chaque simulation peut contenir 1000+ points de trajectoire (~500KB par requête)

---

## 🔐 Sécurité

- **Ne jamais commit le fichier `.env`** (déjà dans `.gitignore`)
- Les credentials Supabase doivent rester privés
- Pas d'authentification implémentée pour l'instant

---

## 📞 Support

Pour toute question, consulter :
- Documentation FastAPI : https://fastapi.tiangolo.com/
- Documentation Supabase : https://supabase.com/docs
- Documentation Pydantic : https://docs.pydantic.dev/
