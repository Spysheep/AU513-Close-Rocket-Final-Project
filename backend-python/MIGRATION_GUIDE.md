# Guide de Migration - Endpoint /predict

## 🎯 Changement de Structure

L'endpoint `/predict` a été adapté pour correspondre exactement à la structure envoyée par le frontend Next.js.

---

## ❌ Ancienne Structure (v2.0.0)

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

**Problème** : Cette structure correspond au dataset CSV (1000 simulations), pas au formulaire frontend.

---

## ✅ Nouvelle Structure (v2.1.0)

```json
{
  "geometry": {
    "coiffe": {
      "shape_param": 0.5,
      "diameter_mm": 60,
      "length_mm": 150
    },
    "tube": {
      "diameter_mm": 60,
      "length_mm": 300
    },
    "aileron": {
      "type": "trapezoidale",
      "number": 3,
      "inclination_deg": 0
    }
  },
  "cg": {
    "x": 0.0,
    "y": 0.0,
    "z": 0.2
  },
  "weight_kg": 1.5,
  "thrust_N": 50.0,
  "wind": {
    "x": 0.0,
    "y": 0.0,
    "z": 0.0,
    "groundSpeed_kms": 0.0
  },
  "ramp_inclination": {
    "theta_xy": 0.0,
    "phi_xz": 85.0
  }
}
```

**Avantage** : Structure organisée hiérarchiquement, correspond exactement au frontend.

---

## 📊 Mapping des Champs

| Ancienne Structure | Nouvelle Structure |
|--------------------|-------------------|
| `cone_length` | `geometry.coiffe.length_mm` |
| `radius` | `geometry.coiffe.diameter_mm` / 2 |
| `rocket_length` | `geometry.tube.length_mm` |
| `fin_cat` | `geometry.aileron.type` |
| `number_of_ailerons` | `geometry.aileron.number` |
| `fin_inclinaison` | `geometry.aileron.inclination_deg` |
| `mass` | `weight_kg` |
| N/A (calculé) | `thrust_N` |
| N/A | `cg.x`, `cg.y`, `cg.z` |
| N/A | `wind.x`, `wind.y`, `wind.z`, `wind.groundSpeed_kms` |
| N/A | `ramp_inclination.theta_xy`, `ramp_inclination.phi_xz` |

---

## 🔄 Exemple de Migration

### Avant (Python/JavaScript)

```python
payload = {
    "delay": 0.0,
    "heading": 25.62,
    "motor_name": "Pro75M1670",
    "radius": 0.03,  # 30mm
    "mass": 1.5,
    "fin_cat": "trapezoidal",
    "number_of_ailerons": 4
}
```

### Après (Python/JavaScript)

```python
payload = {
    "geometry": {
        "coiffe": {
            "shape_param": 0.5,
            "diameter_mm": 60,  # 2 × radius
            "length_mm": 150
        },
        "tube": {
            "diameter_mm": 60,
            "length_mm": 300
        },
        "aileron": {
            "type": "trapezoidale",
            "number": 4,
            "inclination_deg": 0
        }
    },
    "cg": {"x": 0.0, "y": 0.0, "z": 0.2},
    "weight_kg": 1.5,
    "thrust_N": 50.0,
    "wind": {"x": 0.0, "y": 0.0, "z": 0.0, "groundSpeed_kms": 0.0},
    "ramp_inclination": {"theta_xy": 0.0, "phi_xz": 85.0}
}
```

---

## 🧪 Test de Migration

Utilisez ce code Python pour tester votre payload :

```python
import json
from main import PredictRequest

# Votre nouvelle payload
payload = {
    "geometry": {
        "coiffe": {"shape_param": 0.5, "diameter_mm": 60, "length_mm": 150},
        "tube": {"diameter_mm": 60, "length_mm": 300},
        "aileron": {"type": "trapezoidale", "number": 3, "inclination_deg": 0}
    },
    "cg": {"x": 0.0, "y": 0.0, "z": 0.2},
    "weight_kg": 1.5,
    "thrust_N": 50.0,
    "wind": {"x": 0.0, "y": 0.0, "z": 0.0, "groundSpeed_kms": 0.0},
    "ramp_inclination": {"theta_xy": 0.0, "phi_xz": 85.0}
}

# Valider avec Pydantic
try:
    request = PredictRequest(**payload)
    print("✅ Validation OK!")
    print(f"Type aileron: {request.geometry.aileron.type}")
    print(f"Poids: {request.weight_kg} kg")
    print(f"Poussée: {request.thrust_N} N")
except Exception as e:
    print(f"❌ Erreur de validation: {e}")
```

---

## 🚀 Commandes de Test

### Test avec curl

```bash
curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -d @predict_example.json
```

### Test avec Python requests

```python
import requests

response = requests.post(
    "http://localhost:8000/predict",
    json=payload
)

print(response.status_code)
print(response.json())
```

---

## ⚠️ Validations à Respecter

### Geometry

- **shape_param** : 0 ≤ valeur ≤ 1
- **diameter_mm** : > 0
- **length_mm** : > 0
- **type d'aileron** : "trapezoidale", "elliptique" ou "diamant"
- **number d'ailerons** : ≥ 3

### Autres Champs

- **weight_kg** : > 0
- **thrust_N** : > 0
- **Angles** : -360° ≤ valeur ≤ 360°

---

## 📝 Réponse Attendue

```json
{
  "status": "success",
  "message": "Paramètres de fusée reçus et validés. Géométrie: coiffe 0.5 (60mm × 150mm), tube 60mm × 300mm, 3 ailerons trapezoidale. Masse: 1.5kg, Poussée: 50.0N (T/W: 3.40). Modèle ML non encore implémenté.",
  "request_id": null
}
```

Le message inclut maintenant :
- ✅ Résumé de la géométrie
- ✅ Masse et poussée
- ✅ **Ratio Poussée/Poids (T/W)** calculé automatiquement

---

## 🔗 Ressources

- **Fichier d'exemple** : `predict_example.json`
- **Tests** : `test_api.py` (fonction `test_predict_valid()`)
- **Documentation** : `README.md`
- **Changelog** : `CHANGELOG.md`

---

## 💡 Questions Fréquentes

### Q: Pourquoi ce changement ?

**R:** Pour synchroniser parfaitement le backend avec le frontend Next.js. La nouvelle structure correspond exactement au formulaire utilisateur.

### Q: L'endpoint `/simulations` a-t-il changé ?

**R:** Non, `/simulations` garde sa structure d'origine car il récupère les données du dataset Supabase (1000 simulations).

### Q: Puis-je encore utiliser l'ancienne structure ?

**R:** Non, l'ancienne structure n'est plus supportée depuis la v2.1.0. Vous devez migrer vos requêtes.

### Q: Le modèle ML est-il implémenté ?

**R:** Non, l'endpoint `/predict` valide les données et retourne un accusé de réception. L'intégration ML est prévue pour une version future.
