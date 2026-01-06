
import numpy as np
import matplotlib.pyplot as plt
from RocketCreator import RocketCreator

def test_wind(wx, wy, label):
    print(f"\nScanning Wind: X={wx}, Y={wy}")
    rocket = RocketCreator(wind_velocity_x=wx, wind_velocity_y=wy)
    flight = rocket.flight
    
    # Robust extraction
    t_data = flight.time
    
    val = flight.x
    if callable(val):
        xs = val(t_data)
    elif isinstance(val, np.ndarray):
        xs = val
    else:
        xs = np.array(val)
        
    final_x = float(xs[-1]) if xs.ndim == 1 else float(xs[-1][0])

    val_y = flight.y
    if callable(val_y):
        ys = val_y(t_data)
    elif isinstance(val_y, np.ndarray):
        ys = val_y
    else:
        ys = np.array(val_y)
        
    final_y = float(ys[-1]) if ys.ndim == 1 else float(ys[-1][0])
    
    print(f"Final Position: X={final_x:.2f}, Y={final_y:.2f}")
    if abs(final_x) > 10:
        drift_dir = "POSITIVE X" if final_x > 0 else "NEGATIVE X"
        print(f"Drift Direction: {drift_dir}")
    else:
        print("Drift: Negligible")
        
    return final_x

print("Running wind sign verification...")

# Case 1: Negative Wind X
x_neg = test_wind(-5.0, 0, "Negative Wind (-5)")

# Case 2: Positive Wind X
x_pos = test_wind(5.0, 0, "Positive Wind (+5)")

if x_neg < 0 and x_pos > 0:
    print("\nCONCLUSION: RocketPy drifts WITH the wind direction (or wind is defined as 'blowing to').")
elif x_neg > 0 and x_pos < 0:
    print("\nCONCLUSION: RocketPy weather-cocks INTO the wind (standard physics).")
else:
    print("\nCONCLUSION: Ambiguous or complex behavior.")
