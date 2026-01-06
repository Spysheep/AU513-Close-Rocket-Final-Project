import pandas as pd
import numpy as np

# Load training data
df = pd.read_csv('dataset_tensorflow.csv')

print('='*70)
print('ANALYZING TRAINING DATA COORDINATE SYSTEM')
print('='*70)

# Find a trajectory with minimal wind to understand heading behavior
print('\nLooking for trajectory with minimal wind...')

# Group by simulation and get wind stats
sim_groups = df.groupby('simulation_id')
wind_magnitudes = sim_groups.apply(
    lambda g: np.sqrt(g['wind_velocity_x'].iloc[0]**2 + g['wind_velocity_y'].iloc[0]**2)
)

# Get simulation with minimal wind
min_wind_sim_id = wind_magnitudes.idxmin()
sim = df[df['simulation_id'] == min_wind_sim_id].copy()

print(f'\nSimulation ID: {min_wind_sim_id}')
print(f'Heading: {sim["heading"].iloc[0]:.4f} radians ({np.degrees(sim["heading"].iloc[0]):.1f}°)')
print(f'Wind X: {sim["wind_velocity_x"].iloc[0]:.3f} m/s')
print(f'Wind Y: {sim["wind_velocity_y"].iloc[0]:.3f} m/s')
print(f'Ramp inclination: {sim["ramp_inclinaison"].iloc[0]:.1f}°')

# Analyze trajectory
print(f'\nTrajectory analysis:')
print(f'  Duration: {sim["time"].iloc[-1]:.2f} seconds')
print(f'  Data points: {len(sim)}')

# Final position
final = sim.iloc[-1]
print(f'\nFinal position:')
print(f'  X: {final["x"]:8.2f} m')
print(f'  Y: {final["y"]:8.2f} m')
print(f'  Z: {final["z"]:8.2f} m')

# Apogee
apogee_idx = sim['z'].idxmax()
apogee = sim.loc[apogee_idx]
print(f'\nApogee:')
print(f'  Altitude: {apogee["z"]:.2f} m')
print(f'  Time: {apogee["time"]:.2f} s')
print(f'  X at apogee: {apogee["x"]:.2f} m')
print(f'  Y at apogee: {apogee["y"]:.2f} m')

# Drift analysis
drift_dist = np.sqrt(final['x']**2 + final['y']**2)
drift_angle = np.degrees(np.arctan2(final['y'], final['x']))

print(f'\nHorizontal drift:')
print(f'  Distance: {drift_dist:.2f} m')
print(f'  Direction: {drift_angle:.1f}° from +X axis')
print(f'  Heading was: {np.degrees(sim["heading"].iloc[0]):.1f}°')

# Show trajectory evolution
print(f'\nTrajectory evolution (every 20%):')
sim_reset = sim.reset_index(drop=True)
indices = [int(i * len(sim_reset) / 5) for i in range(6)]
for idx in indices:
    row = sim_reset.iloc[idx]
    print(f'  t={row["time"]:6.2f}s: X={row["x"]:7.2f}, Y={row["y"]:7.2f}, Z={row["z"]:7.2f}')

# Now analyze the specific case from USER_INPUTS
print('\n' + '='*70)
print('FINDING SIMILAR TRAJECTORY TO USER INPUTS')
print('='*70)

# User inputs from predict_user_trajectory.py
user_heading = 0  # degrees
user_wind_x = -0.4
user_wind_y = -4.4

# Find similar trajectory
print(f'\nSearching for trajectory with:')
print(f'  Heading ≈ {user_heading}° ({np.radians(user_heading):.4f} rad)')
print(f'  Wind X ≈ {user_wind_x:.2f} m/s')
print(f'  Wind Y ≈ {user_wind_y:.2f} m/s')

# Filter for similar conditions
similar = df[
    (abs(df['heading'] - np.radians(user_heading)) < 0.1) &
    (abs(df['wind_velocity_x'] - user_wind_x) < 0.5) &
    (abs(df['wind_velocity_y'] - user_wind_y) < 0.5)
]

if len(similar) > 0:
    sim_id = similar['simulation_id'].iloc[0]
    sim = df[df['simulation_id'] == sim_id].copy()
    
    print(f'\nFound similar simulation ID: {sim_id}')
    print(f'  Heading: {sim["heading"].iloc[0]:.4f} rad ({np.degrees(sim["heading"].iloc[0]):.1f}°)')
    print(f'  Wind X: {sim["wind_velocity_x"].iloc[0]:.3f} m/s')
    print(f'  Wind Y: {sim["wind_velocity_y"].iloc[0]:.3f} m/s')
    
    # Final position
    final = sim.iloc[-1]
    print(f'\nFinal position:')
    print(f'  X: {final["x"]:8.2f} m')
    print(f'  Y: {final["y"]:8.2f} m')
    print(f'  Z: {final["z"]:8.2f} m')
    
    # Apogee
    apogee_idx = sim['z'].idxmax()
    apogee = sim.loc[apogee_idx]
    print(f'\nApogee:')
    print(f'  Altitude: {apogee["z"]:.2f} m')
    print(f'  X at apogee: {apogee["x"]:.2f} m')
    print(f'  Y at apogee: {apogee["y"]:.2f} m')
    
    # Compare with RocketPy simulation from images
    print(f'\n' + '='*70)
    print('COMPARISON WITH ROCKETPY SIMULATION')
    print('='*70)
    print('\nFrom the uploaded images, RocketPy simulation shows:')
    print('  Apogee: ~2318.7 m')
    print('  Final X: ~-70 m')
    print('  Final Y: ~-200 m')
    print('\nTraining data shows:')
    print(f'  Apogee: {apogee["z"]:.1f} m')
    print(f'  Final X: {final["x"]:.1f} m')
    print(f'  Final Y: {final["y"]:.1f} m')
    
else:
    print('\nNo similar trajectory found in training data')
    print('Showing closest heading=0 trajectories...')
    
    h0 = df[abs(df['heading'] - 0.0) < 0.1]
    if len(h0) > 0:
        # Show first 5 unique simulations
        for sim_id in h0['simulation_id'].unique()[:5]:
            sim = df[df['simulation_id'] == sim_id]
            final = sim.iloc[-1]
            print(f'\n  Sim {sim_id}: Wind=({sim["wind_velocity_x"].iloc[0]:.2f}, {sim["wind_velocity_y"].iloc[0]:.2f}), '
                  f'Final=({final["x"]:.1f}, {final["y"]:.1f}, {final["z"]:.1f})')

print('\n' + '='*70)
