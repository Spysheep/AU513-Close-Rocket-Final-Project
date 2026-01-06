import pandas as pd
import numpy as np

# Load training data
df = pd.read_csv('dataset_tensorflow.csv')

print("="*60)
print("TRAINING DATA ANALYSIS")
print("="*60)

print(f"\nColumns: {df.columns.tolist()}")
print(f"\nTotal rows: {len(df)}")
print(f"Unique simulations: {df['simulation_id'].nunique()}")

# Check heading=0 trajectories
h0 = df[df['heading'] == 0]
print(f"\nRows with heading=0: {len(h0)}")

if len(h0) > 0:
    # Get first simulation with heading=0
    sim_id = h0['simulation_id'].iloc[0]
    sample = df[df['simulation_id'] == sim_id]
    
    print(f"\n{'='*60}")
    print(f"SAMPLE TRAJECTORY (Simulation {sim_id}, heading=0)")
    print(f"{'='*60}")
    print(f"Number of points: {len(sample)}")
    print(f"\nStatistics:")
    print(sample[['x', 'y', 'z', 'heading']].describe())
    
    # Check final position
    final_x = sample['x'].iloc[-1]
    final_y = sample['y'].iloc[-1]
    final_z = sample['z'].iloc[-1]
    
    print(f"\nFinal position:")
    print(f"  X: {final_x:.2f} m")
    print(f"  Y: {final_y:.2f} m")
    print(f"  Z: {final_z:.2f} m")
    
    # Calculate drift direction
    drift_angle = np.degrees(np.arctan2(final_y, final_x))
    print(f"\nDrift direction: {drift_angle:.1f}° from +X axis")
    print(f"Expected for heading=0°: 90° (pure +Y drift)")
    
    # Check wind columns
    if 'wind_velocity_x' in sample.columns and 'wind_velocity_y' in sample.columns:
        print(f"\nWind values:")
        print(f"  wind_velocity_x: {sample['wind_velocity_x'].iloc[0]:.2f} m/s")
        print(f"  wind_velocity_y: {sample['wind_velocity_y'].iloc[0]:.2f} m/s")

# Check a few different headings
print(f"\n{'='*60}")
print("HEADING DISTRIBUTION")
print(f"{'='*60}")
print(df['heading'].value_counts().sort_index())
