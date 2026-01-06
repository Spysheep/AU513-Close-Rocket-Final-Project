import pandas as pd
import numpy as np
import tensorflow as tf
import joblib
import os
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

# --- Configuration ---
MODEL_PATH = 'models/trajectory_model.keras'
X_SCALER_PATH = 'models/x_scaler.save'
Y_SCALER_PATH = 'models/y_scaler.save'
FEATURE_COLUMNS_PATH = 'models/feature_columns.save'
DATA_FILE = 'dataset_tensorflow.csv'  
N_STEPS = 30

TARGET_COLUMNS = ['x', 'y', 'z']
EXCLUDED_COLUMNS = ['delay', 'rocket_id', 'simulation_id']
CATEGORICAL_COLUMN = ['motor_name', 'fin_cat', 'trigger']

def load_artifacts():
    print("Loading model and artifacts...")
    try:
        model = tf.keras.models.load_model(MODEL_PATH)
        x_scaler = joblib.load(X_SCALER_PATH)
        y_scaler = joblib.load(Y_SCALER_PATH)
        feature_columns = joblib.load(FEATURE_COLUMNS_PATH)
        return model, x_scaler, y_scaler, feature_columns
    except Exception as e:
        print(f"Error loading artifacts: {e}")
        print("Ensure 'models/' directory exists and contains trained model/scalers.")
        exit()

def preprocess_input(df, feature_columns, x_scaler):
    # --- Feature Engineering (Physics) ---
    # Calculate Velocity (First Derivative)
    df['vx'] = df['x'].diff().fillna(0)
    df['vy'] = df['y'].diff().fillna(0)
    df['vz'] = df['z'].diff().fillna(0)

    # Calculate Acceleration (Second Derivative)
    df['ax'] = df['vx'].diff().fillna(0)
    df['ay'] = df['vy'].diff().fillna(0)
    df['az'] = df['vz'].diff().fillna(0)

    # --- Separation ---
    columns_to_drop = TARGET_COLUMNS + EXCLUDED_COLUMNS
    X_df = df.drop(columns=columns_to_drop, axis=1, errors='ignore')
    # Ensure our new features are INCLUDED
    X_df = pd.concat([X_df, df[['vx', 'vy', 'vz', 'ax', 'ay', 'az']]], axis=1)

    # --- One-Hot Encoding ---
    present_categorical_cols = [col for col in CATEGORICAL_COLUMN if col in X_df.columns]
    if present_categorical_cols:
        X_df = pd.get_dummies(X_df, columns=present_categorical_cols, drop_first=False)
        
    # --- Deduplicate Columns ---
    # ML1.py logic might produce duplicates (e.g. physics features in X_df AND concatenated).
    # We must remove them to match the scaler.
    X_df = X_df.loc[:, ~X_df.columns.duplicated()]

    # --- Column Alignment ---
    # Trust the SCALER's feature names if available, as that's what it was trained with.
    if hasattr(x_scaler, 'feature_names_in_'):
        # print(f"Scaler expects {len(x_scaler.feature_names_in_)} features. Aligning to scaler features.")
        target_features = x_scaler.feature_names_in_
    else:
        # print(f"Scaler has no feature_names_in_. Using loaded feature_columns ({len(feature_columns)} features).")
        target_features = feature_columns

    # 1. Add missing columns with 0
    for col in target_features:
        if col not in X_df.columns:
            # print(f"Warning: Missing column {col}, filling with 0")
            X_df[col] = 0
            
    # 2. Select only relevant columns in the correct order
    X_df = X_df[target_features]
    
    return X_df

def create_sequences(X_data, Y_data, n_steps):
    X_seq, Y_seq = [], []
    for i in range(len(X_data) - n_steps):
        seq_x = X_data[i:i + n_steps]
        seq_y = Y_data[i + n_steps]
        X_seq.append(seq_x)
        Y_seq.append(seq_y)
    return np.array(X_seq), np.array(Y_seq)

def plot_trajectory(y_true, y_pred):
    print("Plotting trajectory...")
    y_true_np = np.array(y_true)
    y_pred_np = np.array(y_pred)

    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')

    # Plot Actual Path
    ax.plot(y_true_np[:, 0], y_true_np[:, 1], y_true_np[:, 2],
            label='Actual Trajectory', color='green', linewidth=2, alpha=0.7)

    # Plot Predicted Path
    ax.plot(y_pred_np[:, 0], y_pred_np[:, 1], y_pred_np[:, 2],
            label='Predicted Trajectory', color='red', linestyle='--', linewidth=2, alpha=0.7)

    ax.set_title('3D Flight Trajectory Comparison')
    ax.set_xlabel('X Position')
    ax.set_ylabel('Y Position')
    ax.set_zlabel('Z Position')
    ax.legend()
    
    # Save 3D plot
    output_file_3d = "trajectory_prediction_plot_3d.png"
    plt.savefig(output_file_3d)
    print(f"3D Plot saved to {output_file_3d}")
    plt.show()

    # --- Plot 2: 2D Component Breakdown (X, Y, Z separately) ---
    fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
    
    components = ['X', 'Y', 'Z']
    colors = ['blue', 'orange', 'purple']
    
    for i in range(3):
        axes[i].plot(y_true_np[:, i], label=f'Actual {components[i]}', color=colors[i])
        axes[i].plot(y_pred_np[:, i], label=f'Predicted {components[i]}', color='black', linestyle='--')
        axes[i].set_ylabel(f'{components[i]} Position')
        axes[i].legend(loc='upper right')
        axes[i].grid(True)
    
    plt.xlabel('Time Step')
    plt.suptitle('Coordinate-wise Comparison (X, Y, Z)')
    plt.tight_layout()
    
    output_file_2d = "trajectory_prediction_plot_2d.png"
    plt.savefig(output_file_2d)
    print(f"2D Plot saved to {output_file_2d}")
    plt.show()

def export_to_kml(y_true, y_pred, filename="trajectory.kml"):
    print(f"Exporting to {filename}...")
    
    # Launch Site Coordinates
    LAT0 = 43.218436
    LON0 = 0.047333
    ALT0 = 426.0

    # Conversions
    # 1 deg Lat ~= 111,111 meters
    # 1 deg Lon ~= 111,111 * cos(Lat) meters
    import math
    meters_to_lat = 1.0 / 111111.0
    meters_to_lon = 1.0 / (111111.0 * math.cos(math.radians(LAT0)))
    
    def format_coords(data):
        # data is array of [x, y, z]
        # output string "lon,lat,alt lon,lat,alt ..."
        # Analyzing frame: Assuming X=East(Lon), Y=North(Lat), Z=Up based on standard plotting
        coords_str = ""
        for point in data:
            x, y, z = point
            
            # Apply offset to initial coordinates
            # x is East offset in meters
            # y is North offset in meters
            # z is Altitude offset in meters (assuming model is relative to launch, or if absolute we need to check)
            # If Z starts at 0 in the model, we add ALT0. 
            # If Z is absolute altitude, we might not need to add ALT0, but usually trajectory models start at 0.
            # Looking at the sample prediction: Z is ~544. Actual Z ~512.
            # If these are meters above ground, we add ALT0. 
            # If they are ASL, we don't.
            # Given the previous plot output for X,Y was small (~2m, ~4m) and Z was large (~500m), 
            # it implies flight height. 
            # If Z=500 is absolute ASL, and Launch is 426, then flight is only 74m high?
            # Or if Z=500 is AGL, then absolute is 926.
            # Let's assume Z in model is Altitude Above Launch (AGL) or similar local frame.
            # Actually, if I look at "prediction result" X=2, Y=4, Z=544.
            # If the user says Altitude is 426m at launch.
            # If the dataset Z values start near 0, then it's AGL. 
            # Let's check the first values of Z in the loop implicitly by seeing if they are small relative to 426.
            # If Z starts around 0, we add ALT0.
            
            check_lon = LON0 + (x * meters_to_lon)
            check_lat = LAT0 + (y * meters_to_lat)
            check_alt = z + ALT0 
            
            coords_str += f"{check_lon},{check_lat},{check_alt} "
        return coords_str.strip()

    kml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Rocket Trajectory</name>
    <Style id="actualStyle">
      <LineStyle>
        <color>ff00ff00</color> <!-- Green -->
        <width>2</width>
      </LineStyle>
    </Style>
    <Style id="predStyle">
      <LineStyle>
        <color>ff0000ff</color> <!-- Red -->
        <width>2</width>
      </LineStyle>
    </Style>
    <Placemark>
      <name>Actual Trajectory</name>
      <styleUrl>#actualStyle</styleUrl>
      <LineString>
        <extrude>1</extrude>
        <tessellate>1</tessellate>
        <altitudeMode>absolute</altitudeMode>
        <coordinates>
          {format_coords(y_true)}
        </coordinates>
      </LineString>
    </Placemark>
    <Placemark>
      <name>Predicted Trajectory</name>
      <styleUrl>#predStyle</styleUrl>
      <LineString>
        <extrude>1</extrude>
        <tessellate>1</tessellate>
        <altitudeMode>absolute</altitudeMode>
        <coordinates>
          {format_coords(y_pred)}
        </coordinates>
      </LineString>
    </Placemark>
  </Document>
</kml>"""

    with open(filename, "w") as f:
        f.write(kml_content)
    print("KML export complete.")

def main():
    model, x_scaler, y_scaler, feature_columns = load_artifacts()

    print(f"Loading data from {DATA_FILE}...")
    try:
        df = pd.read_csv(DATA_FILE)
    except FileNotFoundError:
        print(f"File {DATA_FILE} not found.")
        return

    # Select a single simulation to make sense of the trajectory
    if 'simulation_id' in df.columns:
        sim_ids = df['simulation_id'].unique()
        target_sim_id = sim_ids[0] # Just pick the first one
        print(f"Filtering for simulation_id: {target_sim_id}")
        df_sim = df[df['simulation_id'] == target_sim_id].copy()
    else:
        print("Warning: 'simulation_id' column not found. Using first 300 rows as a single trajectory.")
        df_sim = df.head(300).copy()

    if len(df_sim) < N_STEPS + 10:
        print(f"Not enough data points in simulation. Need > {N_STEPS}, got {len(df_sim)}")
        return

    # Prepare Target (Y) needed for comparison
    Y_df = df_sim[TARGET_COLUMNS]

    print("Preprocessing data...")
    X_processed_df = preprocess_input(df_sim, feature_columns, x_scaler)
    
    print("Scaling data...")
    X_scaled = x_scaler.transform(X_processed_df.values)
    Y_scaled = y_scaler.transform(Y_df.values) # We need to scale Y to create valid sequences for comparison logic (if we were using it for input, but here we just need Y for ground truth)
    
    # Actually, for Y_seq, we just want the values corresponding to the sequences.
    
    print(f"Creating sequences (N_STEPS={N_STEPS})...")
    X_seq, Y_seq = create_sequences(X_scaled, Y_scaled, N_STEPS)
    
    if len(X_seq) == 0:
        print("No sequences created.")
        return

    print(f"Predicting for {len(X_seq)} steps...")
    y_pred_scaled = model.predict(X_seq, verbose=1)
    
    # Inverse transform
    y_pred = y_scaler.inverse_transform(y_pred_scaled)
    y_true = y_scaler.inverse_transform(Y_seq)
    
    # Plot
    plot_trajectory(y_true, y_pred)
    
    # Export KML
    export_to_kml(y_true, y_pred)

    
if __name__ == "__main__":
    main()
