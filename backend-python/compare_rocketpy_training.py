import pandas as pd
import numpy as np
from RocketCreator import RocketCreator

print("="*60)
print("COMPARING ROCKETPY OUTPUT WITH TRAINING DATA")
print("="*60)

# Load a sample from training data
df = pd.read_csv('dataset_tensorflow.csv')

# Get first simulation
sim_id = df['simulation_id'].iloc[0]
training_sample = df[df['simulation_id'] == sim_id].iloc[0]

print("\nTRAINING DATA SAMPLE (first row of first simulation):")
print(f"  heading: {training_sample['heading']:.6f}")
print(f"  wind_velocity_x: {training_sample['wind_velocity_x']:.6f}")
print(f"  wind_velocity_y: {training_sample['wind_velocity_y']:.6f}")
print(f"  ramp_inclinaison: {training_sample['ramp_inclinaison']:.6f}")
print(f"  x: {training_sample['x']:.6f}")
print(f"  y: {training_sample['y']:.6f}")
print(f"  z: {training_sample['z']:.6f}")

# Create RocketCreator with same parameters
print("\n" + "="*60)
print("CREATING ROCKETPY SIMULATION WITH SAME PARAMETERS")
print("="*60)

rocket_params = {
    'delay': 0,
    'motor_name': str(training_sample['motor_name']),
    'fin_cat': str(training_sample['fin_cat']),
    'trigger': str(training_sample['trigger']),
    'heading': float(training_sample['heading']),
    'ramp_inclinaison': float(training_sample['ramp_inclinaison']),
    'radius': float(training_sample['radius']),
    'mass': float(training_sample['mass']),
    'inertia': (float(training_sample['ix']), float(training_sample['iy']), float(training_sample['iz'])),
    'center_of_mass_without_motor': float(training_sample['center_of_mass_without_motor']),
    'cone_length': float(training_sample['cone_length']),
    'rocket_length': float(training_sample['rocket_length']),
    'number_of_ailerons': int(training_sample['number_of_ailerons']),
    'root_chord': float(training_sample['root_chord']),
    'tip_chord': float(training_sample['tip_chord']),
    'span': float(training_sample['span']),
    'fins_pos': float(training_sample['fins_pos']),
    'fin_inclinaison': float(training_sample['fin_inclinaison']),
    'drag_coeff': float(training_sample['drag_coeff']),
    'wind_velocity_x': float(training_sample['wind_velocity_x']),
    'wind_velocity_y': float(training_sample['wind_velocity_y']),
}

print(f"\nCreating rocket with heading={rocket_params['heading']:.6f}°")
print(f"Wind: X={rocket_params['wind_velocity_x']:.6f}, Y={rocket_params['wind_velocity_y']:.6f}")

rocket = RocketCreator(**rocket_params)

# Get first few points from RocketPy
flight = rocket.flight
t_data = flight.time[:10]  # First 10 points

def get_col(name, ref_len):
    val = getattr(flight, name, None)
    if val is None: 
        return np.zeros(ref_len)
    if callable(val):
        return val(t_data)
    elif isinstance(val, np.ndarray):
        return val[:ref_len]
    else:
        return np.full(ref_len, val)

x_sim = get_col('x', len(t_data))
y_sim = get_col('y', len(t_data))
z_sim = get_col('z', len(t_data))

print("\nROCKETPY OUTPUT (first point):")
print(f"  x: {x_sim[0]:.6f}")
print(f"  y: {y_sim[0]:.6f}")
print(f"  z: {z_sim[0]:.6f}")

print("\nROCKETPY OUTPUT (10th point):")
print(f"  x: {x_sim[9]:.6f}")
print(f"  y: {y_sim[9]:.6f}")
print(f"  z: {z_sim[9]:.6f}")

# Compare with training data at similar time
training_traj = df[df['simulation_id'] == sim_id]
print(f"\nTRAINING DATA (10th point):")
if len(training_traj) >= 10:
    print(f"  x: {training_traj.iloc[9]['x']:.6f}")
    print(f"  y: {training_traj.iloc[9]['y']:.6f}")
    print(f"  z: {training_traj.iloc[9]['z']:.6f}")

# Check final positions
print("\n" + "="*60)
print("FINAL POSITIONS")
print("="*60)

x_final_sim = get_col('x', len(flight.time))[-1]
y_final_sim = get_col('y', len(flight.time))[-1]
z_final_sim = get_col('z', len(flight.time))[-1]

print(f"\nROCKETPY FINAL:")
print(f"  x: {x_final_sim:.2f}")
print(f"  y: {y_final_sim:.2f}")
print(f"  z: {z_final_sim:.2f}")
print(f"  Max altitude: {np.max(get_col('z', len(flight.time))):.2f}")

print(f"\nTRAINING DATA FINAL:")
print(f"  x: {training_traj.iloc[-1]['x']:.2f}")
print(f"  y: {training_traj.iloc[-1]['y']:.2f}")
print(f"  z: {training_traj.iloc[-1]['z']:.2f}")
print(f"  Max altitude: {training_traj['z'].max():.2f}")

# Calculate drift angles
rocketpy_angle = np.degrees(np.arctan2(y_final_sim, x_final_sim))
training_angle = np.degrees(np.arctan2(training_traj.iloc[-1]['y'], training_traj.iloc[-1]['x']))

print(f"\nDRIFT DIRECTION:")
print(f"  RocketPy: {rocketpy_angle:.1f}°")
print(f"  Training: {training_angle:.1f}°")
print(f"  Heading: {rocket_params['heading']:.1f}°")
