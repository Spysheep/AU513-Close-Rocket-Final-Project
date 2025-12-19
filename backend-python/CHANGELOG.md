# Changelog - Backend API Close Rocket

## Version 2.1.0 - Adaptation Frontend (2025-12-19)

### ✨ Changements Majeurs

#### Endpoint `/predict` - Structure Adaptée au Frontend

**Avant** : L'endpoint acceptait 20 paramètres individuels provenant du dataset (delay, heading, motor_name, radius, mass, etc.)

**Maintenant** : L'endpoint accepte la structure exacte envoyée par le frontend Next.js avec organisation hiérarchique :

```json
{
  "geometry": {
    "coiffe": { "shape_param", "diameter_mm", "length_mm" },
    "tube": { "diameter_mm", "length_mm" },
    "aileron": { "type", "number", "inclination_deg" }
  },
  "cg": { "x", "y", "z" },
  "weight_kg": float,
  "thrust_N": float,
  "wind": { "x", "y", "z", "groundSpeed_kms" },
  "ramp_inclination": { "theta_xy", "phi_xz" }
}
```

### 📋 Nouveaux Modèles Pydantic

**7 nouveaux modèles** pour valider la structure complète :

1. **CoiffeGeometry** : Paramètres de la coiffe (shape_param 0-1, dimensions)
2. **TubeGeometry** : Dimensions du tube
3. **AileronGeometry** : Type d'aileron (trapezoidale, elliptique, diamant), nombre (min 3)
4. **Geometry** : Conteneur pour coiffe + tube + aileron
5. **CenterOfGravity** : Coordonnées x, y, z du centre de gravité
6. **Wind** : Conditions de vent (x, y, z, groundSpeed_kms)
7. **RampInclination** : Angles de la rampe (theta_xy, phi_xz)

Le modèle **PredictRequest** a été complètement réécrit pour utiliser ces sous-modèles.

### 🔍 Nouvelles Validations

- `shape_param` : 0 ≤ valeur ≤ 1
- `diameter_mm`, `length_mm` : > 0
- `type` d'aileron : "trapezoidale", "elliptique" ou "diamant"
- `number` d'ailerons : ≥ 3
- `weight_kg`, `thrust_N` : > 0
- Angles de rampe : -360° ≤ valeur ≤ 360°

### 📊 Calcul Automatique

L'endpoint `/predict` calcule maintenant automatiquement :
- **Rapport Poussée/Poids (T/W)** : `thrust_N / (weight_kg × 9.81)`
- Inclus dans le message de réponse pour validation utilisateur

### 📝 Réponse Enrichie

**Avant** :
```json
{
  "status": "success",
  "message": "Paramètres reçus et validés. Modèle ML non implémenté.",
  "request_id": null
}
```

**Maintenant** :
```json
{
  "status": "success",
  "message": "Paramètres de fusée reçus et validés. Géométrie: coiffe 0.5 (60mm × 150mm), tube 60mm × 300mm, 3 ailerons trapezoidale. Masse: 1.5kg, Poussée: 50.0N (T/W: 3.40). Modèle ML non encore implémenté.",
  "request_id": null
}
```

### 🧪 Tests Mis à Jour

Le fichier `test_api.py` a été mis à jour avec 9 tests :
1. ✅ Root endpoint
2. ✅ Single simulation
3. ✅ Multiple simulations
4. ✅ Invalid ID format
5. ✅ Non-existent ID
6. ✅ **Valid prediction (nouvelle structure)**
7. ✅ **Invalid weight (test de validation)**
8. ✅ **Invalid fin type (test de validation)**
9. ✅ **Invalid shape param (test de validation)**

### 📖 Documentation

- **README.md** : Mis à jour avec la nouvelle structure d'endpoint
- **predict_example.json** : Exemple de payload valide pour le frontend
- **CHANGELOG.md** : Ce fichier

### 🔄 Compatibilité

- ✅ **Frontend** : Compatible avec la structure envoyée par Next.js
- ✅ **Backend** : Validation complète avec Pydantic V2
- ✅ **CORS** : Toujours configuré pour `http://localhost:3000`

### ⚠️ Breaking Changes

L'endpoint `/predict` n'accepte plus l'ancienne structure avec 20 paramètres individuels. Si vous avez des scripts utilisant l'ancienne structure, ils doivent être migrés vers la nouvelle.

---

## Version 2.0.0 - Refonte Complète (2025-12-19)

### Changements Initiaux

- Réécriture complète de `database.py` : SQLite → Supabase
- Réécriture complète de `main.py` : Nouveaux endpoints `/simulations` et `/predict`
- Suppression des anciens endpoints `/calculate` et `/history`
- Ajout de `requirements.txt`
- Documentation complète dans `README.md`
- Script de test `test_api.py`

---

## Versions Précédentes

- **1.0.0** : Version initiale avec SQLite et calcul du carré (démo)
