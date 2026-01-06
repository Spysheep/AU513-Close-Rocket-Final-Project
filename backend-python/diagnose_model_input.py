"""
Diagnostic script to check what the ML model is actually seeing during inference
"""
import pandas as pd
import numpy as np
import joblib

# Load scalers and feature columns
x_scaler = joblib.load('models/x_scaler.save')
y_scaler = joblib.load('models/y_scaler.save')
feature_columns = joblib.load('models/feature_columns.save')

print("="*70)
print("ML MODEL INPUT DIAGNOSTIC")
print("="*70)

# Simulate what happens during the first prediction step
USER_INPUTS = {
    'motor_name': 'Pro75-3G',
    'fin_cat': 'trapezoidal',
    'trigger': 'apogee',
    'wind_velocity_x': -0.4,
    'wind_velocity_y': -4.4,
    'heading': 0,
    'ramp_inclinaison': 80,
    'radius': 0.11,
    'mass': 5.1,
    'center_of_mass_without_motor': 0.7,
    'cone_length': 0.25,
    'rocket_length': 1.540,
    'number_of_ailerons': 4,
    'root_chord': 0.3,
    'tip_chord': 0.1,
    'span': 0.175,
    'fins_pos': 0.04,
    'fin_inclinaison': 0,
    'drag_coeff': 1,
    'ix': 9.7,
    'iy': 9.7,
    'iz': 0,
}

LAUNCH_POSITION = [0.0, 0.0, 460]

# Create initial data (at rest on pad)
base_row = {
    'x': LAUNCH_POSITION[0],
    'y': LAUNCH_POSITION[1],
    'z': LAUNCH_POSITION[2],
    **USER_INPUTS,
    'delay': 0,
    'rocket_id': 0,
    'simulation_id': 0
}

# Create history buffer (30 steps at rest)
DT = 0.01
N_STEPS = 30
initial_data = []

for i in range(N_STEPS):
    row = base_row.copy()
    t = (i - N_STEPS) * DT
    row['time'] = t
    initial_data.append(row)

history_df = pd.DataFrame(initial_data)

print("\n1. INITIAL HISTORY DATA (first 5 rows):")
print(history_df.head())
print(f"\nWind values in history: X={history_df['wind_velocity_x'].iloc[0]}, Y={history_df['wind_velocity_y'].iloc[0]}")
print(f"Position in history: X={history_df['x'].iloc[0]}, Y={history_df['y'].iloc[0]}, Z={history_df['z'].iloc[0]}")

# Apply the same preprocessing as in predict_user_trajectory.py
print("\n2. AFTER FEATURE ENGINEERING:")

df = history_df.copy()
df['vx'] = df['x'].diff().fillna(0)
df['vy'] = df['y'].diff().fillna(0)
df['vz'] = df['z'].diff().fillna(0)

for col in ['vx', 'vy', 'vz']:
    df[col] = df[col].rolling(window=3, min_periods=1).mean()

df['ax'] = df['vx'].diff().fillna(0)
df['ay'] = df['vy'].diff().fillna(0)
df['az'] = df['vz'].diff().fillna(0)

for col in ['ax', 'ay', 'az']:
    df[col] = df[col].rolling(window=3, min_periods=1).mean()

# Drop target columns
TARGET_COLUMNS = ['x', 'y', 'z']
EXCLUDED_COLUMNS = ['delay', 'rocket_id', 'simulation_id']
CATEGORICAL_COLUMN = ['motor_name', 'fin_cat', 'trigger']

columns_to_drop = TARGET_COLUMNS + EXCLUDED_COLUMNS
X_df = df.drop(columns=columns_to_drop, axis=1, errors='ignore')

# Add engineered features explicitly
X_df = pd.concat([X_df, df[['vx', 'vy', 'vz', 'ax', 'ay', 'az']]], axis=1)

# One-hot encode
present_categorical_cols = [col for col in CATEGORICAL_COLUMN if col in X_df.columns]
if present_categorical_cols:
    X_df = pd.get_dummies(X_df, columns=present_categorical_cols, drop_first=False)

# Deduplicate
X_df = X_df.loc[:, ~X_df.columns.duplicated()]

print(f"Columns after preprocessing: {X_df.columns.tolist()}")
print(f"Wind still present: wind_velocity_x in X_df = {'wind_velocity_x' in X_df.columns}")

# Align with feature columns
if hasattr(x_scaler, 'feature_names_in_'):
    target_features = x_scaler.feature_names_in_
else:
    target_features = feature_columns

for col in target_features:
    if col not in X_df.columns:
        X_df[col] = 0

X_df = X_df[target_features]

print("\n3. AFTER ALIGNMENT WITH TRAINING FEATURES:")
print(f"Shape: {X_df.shape}")
print(f"Columns match training: {list(X_df.columns) == list(target_features)}")

# Check wind values
if 'wind_velocity_x' in X_df.columns:
    print(f"\nWind values in aligned features:")
    print(f"  wind_velocity_x: {X_df['wind_velocity_x'].iloc[0]}")
    print(f"  wind_velocity_y: {X_df['wind_velocity_y'].iloc[0]}")
else:
    print("\n⚠️  WARNING: Wind features missing after alignment!")

# Scale
X_scaled = x_scaler.transform(X_df.values)

print("\n4. AFTER SCALING:")
print(f"Scaled data shape: {X_scaled.shape}")
print(f"First row sample (first 10 features):")
print(X_scaled[0, :10])

print("\n5. CHECKING SCALER STATISTICS:")
if hasattr(x_scaler, 'mean_'):
    print(f"Scaler mean for wind_velocity_x: {x_scaler.mean_[list(target_features).index('wind_velocity_x') if 'wind_velocity_x' in target_features else -1]}")
    print(f"Scaler scale for wind_velocity_x: {x_scaler.scale_[list(target_features).index('wind_velocity_x') if 'wind_velocity_x' in target_features else -1]}")

print("\n" + "="*70)
print("DIAGNOSTIC COMPLETE")
print("="*70)
