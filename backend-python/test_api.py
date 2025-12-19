"""
Script de test pour l'API Close Rocket
Teste les endpoints /simulations et /predict avec la nouvelle structure
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_root():
    """Test l'endpoint racine"""
    print("\n=== Test 1: Endpoint racine (/) ===")
    response = requests.get(f"{BASE_URL}/")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200


def test_simulations_single():
    """Test l'endpoint /simulations avec un seul ID"""
    print("\n=== Test 2: /simulations avec un seul ID (rocket_0000) ===")
    response = requests.get(f"{BASE_URL}/simulations?ids=rocket_0000")
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Count: {data['count']}")
        if data['simulations']:
            sim = data['simulations'][0]
            print(f"Rocket ID: {sim['rocket_id']}")
            print(f"Motor: {sim['rocket_parameters']['motor_name']}")
            print(f"Trajectory points: {sim['metadata']['total_points']}")
            print(f"Max altitude: {sim['metadata']['max_altitude']:.2f} m")
            print(f"Duration: {sim['metadata']['duration']:.2f} s")
    else:
        print(f"Error: {response.json()}")

    return response.status_code == 200


def test_simulations_multiple():
    """Test l'endpoint /simulations avec plusieurs IDs"""
    print("\n=== Test 3: /simulations avec plusieurs IDs (rocket_0000, rocket_0001) ===")
    response = requests.get(f"{BASE_URL}/simulations?ids=rocket_0000,rocket_0001")
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Count: {data['count']}")
        for sim in data['simulations']:
            print(f"  - {sim['rocket_id']}: {sim['metadata']['total_points']} points, max alt: {sim['metadata']['max_altitude']:.2f} m")
    else:
        print(f"Error: {response.json()}")

    return response.status_code == 200


def test_simulations_invalid_format():
    """Test l'endpoint /simulations avec un format invalide"""
    print("\n=== Test 4: /simulations avec format invalide (rocket_abc) ===")
    response = requests.get(f"{BASE_URL}/simulations?ids=rocket_abc")
    print(f"Status: {response.status_code}")
    print(f"Error: {response.json()}")
    return response.status_code == 400


def test_simulations_not_found():
    """Test l'endpoint /simulations avec un ID inexistant"""
    print("\n=== Test 5: /simulations avec ID inexistant (rocket_9999) ===")
    response = requests.get(f"{BASE_URL}/simulations?ids=rocket_9999")
    print(f"Status: {response.status_code}")
    print(f"Error: {response.json()}")
    return response.status_code == 404


def test_predict_valid():
    """Test l'endpoint /predict avec des paramètres valides"""
    print("\n=== Test 6: /predict avec paramètres valides ===")

    payload = {
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

    response = requests.post(f"{BASE_URL}/predict", json=payload)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    else:
        print(f"Error: {response.text}")
    return response.status_code == 200


def test_predict_invalid_weight():
    """Test l'endpoint /predict avec poids négatif"""
    print("\n=== Test 7: /predict avec poids négatif ===")

    payload = {
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
        "weight_kg": -1.5,  # Invalid (negative)
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

    response = requests.post(f"{BASE_URL}/predict", json=payload)
    print(f"Status: {response.status_code}")
    print(f"Error: {response.json()}")
    return response.status_code == 422


def test_predict_invalid_fin_type():
    """Test l'endpoint /predict avec type d'aileron invalide"""
    print("\n=== Test 8: /predict avec type d'aileron invalide ===")

    payload = {
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
                "type": "invalid_type",  # Invalid
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

    response = requests.post(f"{BASE_URL}/predict", json=payload)
    print(f"Status: {response.status_code}")
    print(f"Error: {response.json()}")
    return response.status_code == 422


def test_predict_invalid_shape_param():
    """Test l'endpoint /predict avec shape_param hors limites"""
    print("\n=== Test 9: /predict avec shape_param > 1 ===")

    payload = {
        "geometry": {
            "coiffe": {
                "shape_param": 1.5,  # Invalid (should be 0-1)
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

    response = requests.post(f"{BASE_URL}/predict", json=payload)
    print(f"Status: {response.status_code}")
    print(f"Error: {response.json()}")
    return response.status_code == 422


def run_all_tests():
    """Exécute tous les tests"""
    print("=" * 80)
    print("TEST DE L'API CLOSE ROCKET")
    print("=" * 80)
    print("\nAssurez-vous que l'API est lancée avec: uvicorn main:app --reload")
    print("Appuyez sur Entrée pour commencer les tests...")
    input()

    tests = [
        ("Root endpoint", test_root),
        ("Single simulation", test_simulations_single),
        ("Multiple simulations", test_simulations_multiple),
        ("Invalid ID format", test_simulations_invalid_format),
        ("Non-existent ID", test_simulations_not_found),
        ("Valid prediction", test_predict_valid),
        ("Invalid weight", test_predict_invalid_weight),
        ("Invalid fin type", test_predict_invalid_fin_type),
        ("Invalid shape param", test_predict_invalid_shape_param),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\nERREUR lors du test '{test_name}': {e}")
            results.append((test_name, False))

    # Résumé
    print("\n" + "=" * 80)
    print("RÉSUMÉ DES TESTS")
    print("=" * 80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{status}: {test_name}")

    print(f"\nRésultat: {passed}/{total} tests réussis")
    print("=" * 80)


if __name__ == "__main__":
    run_all_tests()
