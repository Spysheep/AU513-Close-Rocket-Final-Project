import pandas as pd
import numpy as np

# Load training data
df = pd.read_csv('dataset_tensorflow.csv')

print('='*70)
print('DETAILED TRAJECTORY ANALYSIS')
print('='*70)

# Get first simulation
sim_id = df['simulation_id'].iloc[0]
sim = df[df['simulation_id'] == sim_id].copy()

heading = sim['heading'].iloc[0]
wind_x = sim['wind_velocity_x'].iloc[0]
wind_y = sim['wind_velocity_y'].iloc[0]
ramp_incl = sim['ramp_inclinaison'].iloc[0]

print(f'\nSimulation ID: {sim_id}')
print(f'Heading: {heading:.2f}°')
print(f'Wind X: {wind_x:.2f} m/s')
print(f'Wind Y: {wind_y:.2f} m/s')
print(f'Ramp inclination: {ramp_incl:.2f}°')

# Get apogee (max Z)
apogee_idx = sim['z'].idxmax()
apogee = sim.loc[apogee_idx]

print(f'\nApogee:')
print(f'  Time: {apogee["time"]:.2f} s')
print(f'  X: {apogee["x"]:.2f} m')
print(f'  Y: {apogee["y"]:.2f} m')
print(f'  Z: {apogee["z"]:.2f} m')

# Final position
final = sim.iloc[-1]
print(f'\nFinal position:')
print(f'  Time: {final["time"]:.2f} s')
print(f'  X: {final["x"]:.2f} m')
print(f'  Y: {final["y"]:.2f} m')
print(f'  Z: {final["z"]:.2f} m')

# Calculate drift
drift_dist = np.sqrt(final['x']**2 + final['y']**2)
drift_angle = np.degrees(np.arctan2(final['y'], final['x']))

print(f'\nHorizontal drift:')
print(f'  Distance: {drift_dist:.2f} m')
print(f'  Direction: {drift_angle:.2f}° from +X axis')

# Expected drift direction based on heading and wind
print(f'\nExpected drift based on heading={heading:.2f}°:')
print(f'  If heading points in direction of +Y at 0°, then:')
print(f'    - Heading {heading:.2f}° should drift at angle {heading:.2f}°')
print(f'  Actual drift angle: {drift_angle:.2f}°')
print(f'  Difference: {abs(drift_angle - heading):.2f}°')

# Wind contribution
wind_angle = np.degrees(np.arctan2(wind_y, wind_x))
wind_mag = np.sqrt(wind_x**2 + wind_y**2)
print(f'\nWind analysis:')
print(f'  Wind magnitude: {wind_mag:.2f} m/s')
print(f'  Wind direction: {wind_angle:.2f}° from +X axis')

# Show trajectory samples
print(f'\nTrajectory samples (every 10% of flight):')
print(f'{"Time":>8} {"X":>10} {"Y":>10} {"Z":>10}')
print('-' * 42)
indices = [int(i * len(sim) / 10) for i in range(11)]
for idx in indices:
    row = sim.iloc[idx]
    print(f'{row["time"]:8.2f} {row["x"]:10.2f} {row["y"]:10.2f} {row["z"]:10.2f}')

# Analyze X and Y ranges
print(f'\nCoordinate statistics:')
print(f'  X range: [{sim["x"].min():.2f}, {sim["x"].max():.2f}] m')
print(f'  Y range: [{sim["y"].min():.2f}, {sim["y"].max():.2f}] m')
print(f'  Z range: [{sim["z"].min():.2f}, {sim["z"].max():.2f}] m')

# Check a few more simulations
print('\n' + '='*70)
print('COMPARING MULTIPLE SIMULATIONS')
print('='*70)

for i in range(min(5, df['simulation_id'].nunique())):
    sim_id = df['simulation_id'].unique()[i]
    sim = df[df['simulation_id'] == sim_id]
    
    heading = sim['heading'].iloc[0]
    final = sim.iloc[-1]
    
    drift_angle = np.degrees(np.arctan2(final['y'], final['x']))
    drift_dist = np.sqrt(final['x']**2 + final['y']**2)
    
    print(f'\nSim {sim_id}: Heading={heading:6.2f}°, Final drift={drift_angle:6.2f}° at {drift_dist:6.1f}m')
    print(f'         Final pos: X={final["x"]:7.2f}, Y={final["y"]:7.2f}, Z={final["z"]:7.2f}')

print('\n' + '='*70)
