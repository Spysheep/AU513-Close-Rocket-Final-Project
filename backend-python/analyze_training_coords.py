import pandas as pd
import numpy as np

# Load training data
df = pd.read_csv('dataset_tensorflow.csv')

print('='*60)
print('TRAINING DATA ANALYSIS')
print('='*60)
print(f'Total rows: {len(df)}')
print(f'Total simulations: {df["simulation_id"].nunique()}')

# Check heading values
print(f'\nHeading values (unique): {sorted(df["heading"].unique())[:15]}...')

# Analyze a trajectory with heading=0
print('\n' + '='*60)
print('ANALYZING HEADING=0 TRAJECTORY')
print('='*60)

# Find trajectories with heading close to 0
h0_sims = df[abs(df['heading'] - 0.0) < 0.1]

if len(h0_sims) > 0:
    # Get first simulation with heading~0
    sim_id = h0_sims['simulation_id'].iloc[0]
    sim = df[df['simulation_id'] == sim_id].copy()
    
    print(f'\nSimulation ID: {sim_id}')
    print(f'Heading: {sim["heading"].iloc[0]:.2f}°')
    print(f'Wind X: {sim["wind_velocity_x"].iloc[0]:.2f} m/s')
    print(f'Wind Y: {sim["wind_velocity_y"].iloc[0]:.2f} m/s')
    print(f'Ramp inclination: {sim["ramp_inclinaison"].iloc[0]:.2f}°')
    
    # Get final position
    final = sim.iloc[-1]
    print(f'\nFinal position:')
    print(f'  X: {final["x"]:.2f} m')
    print(f'  Y: {final["y"]:.2f} m')
    print(f'  Z: {final["z"]:.2f} m')
    
    # Calculate drift direction
    drift_angle = np.degrees(np.arctan2(final['y'], final['x']))
    drift_dist = np.sqrt(final['x']**2 + final['y']**2)
    
    print(f'\nHorizontal drift:')
    print(f'  Distance: {drift_dist:.2f} m')
    print(f'  Direction: {drift_angle:.2f}° from +X axis')
    print(f'  Expected for heading=0°: 90° (pure +Y direction)')
    
    # Show trajectory evolution
    print(f'\nTrajectory evolution (every 20% of flight):')
    indices = [int(i * len(sim) / 5) for i in range(6)]
    for idx in indices:
        row = sim.iloc[idx]
        print(f'  t={row["time"]:6.2f}s: X={row["x"]:7.2f}, Y={row["y"]:7.2f}, Z={row["z"]:7.2f}')
    
    # Check if X stays near 0 for heading=0
    max_x = sim['x'].abs().max()
    max_y = sim['y'].abs().max()
    
    print(f'\nCoordinate ranges:')
    print(f'  Max |X|: {max_x:.2f} m')
    print(f'  Max |Y|: {max_y:.2f} m')
    
    if max_x < max_y / 5:
        print('\n✓ EXPECTED: For heading=0°, X should be small, Y should be large')
        print('  This suggests: X=East-West, Y=North-South, heading=0° points North')
    else:
        print('\n⚠ UNEXPECTED: X and Y magnitudes are similar')
        print('  This suggests a different coordinate convention')
else:
    print('No trajectories with heading=0 found')

# Analyze a trajectory with heading=90
print('\n' + '='*60)
print('ANALYZING HEADING=90 TRAJECTORY')
print('='*60)

h90_sims = df[abs(df['heading'] - 90.0) < 0.1]

if len(h90_sims) > 0:
    sim_id = h90_sims['simulation_id'].iloc[0]
    sim = df[df['simulation_id'] == sim_id].copy()
    
    print(f'\nSimulation ID: {sim_id}')
    print(f'Heading: {sim["heading"].iloc[0]:.2f}°')
    
    final = sim.iloc[-1]
    print(f'\nFinal position:')
    print(f'  X: {final["x"]:.2f} m')
    print(f'  Y: {final["y"]:.2f} m')
    
    max_x = sim['x'].abs().max()
    max_y = sim['y'].abs().max()
    
    print(f'\nCoordinate ranges:')
    print(f'  Max |X|: {max_x:.2f} m')
    print(f'  Max |Y|: {max_y:.2f} m')
    
    if max_x > max_y * 2:
        print('\n✓ EXPECTED: For heading=90°, X should be large, Y should be small')
        print('  This confirms: heading=0° points North, heading=90° points East')
    else:
        print('\n⚠ UNEXPECTED: Coordinate behavior differs from standard convention')
else:
    print('No trajectories with heading=90 found')

print('\n' + '='*60)
