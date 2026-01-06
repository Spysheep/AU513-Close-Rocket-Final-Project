import pandas as pd
import numpy as np
import tensorflow as tf
import joblib
import os
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import math
import warnings
from tqdm import tqdm
from RocketCreator import RocketCreator
warnings.filterwarnings('ignore')

# --- Configuration ---
MODEL_PATH = 'models/trajectory_model.keras'
X_SCALER_PATH = 'models/x_scaler.save'
Y_SCALER_PATH = 'models/y_scaler.save'
FEATURE_COLUMNS_PATH = 'models/feature_columns.save'

# Time step configuration
DT = 0.01  # Time step in seconds (10ms)

def time_to_steps(seconds):
    """
    Convert time in seconds to number of steps based on DT.
    
    Args:
        seconds (float): Time duration in seconds
        
    Returns:
        int: Number of steps corresponding to the time duration
    """
    return int(seconds / DT)

# History window size (time in seconds to use as input context)
HISTORY_TIME = 0.3  # 0.3 seconds of history
N_STEPS = time_to_steps(HISTORY_TIME)

# Prediction duration (how far into the future to predict)
PREDICTION_TIME = 178.5  # 178.5 seconds trajectory prediction
PREDICTION_STEPS = time_to_steps(PREDICTION_TIME)

# --- User Inputs ---
# Define the initial conditions and rocket configuration here.
# NOTE: heading is in DEGREES (same as training data - no conversion needed)
USER_INPUTS = {
    'motor_name': 'Pro75-3G',
    'fin_cat': 'trapezoidal',
    'trigger': 'apogee',
    # Use forecast wind (like training data) instead of constant wind
    'wind_velocity_x': -0.4,
    'wind_velocity_y': -4.4,
    'heading': 0,  # In DEGREES (will be converted to radians for model)
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

# Initial Launch Position (formatted as [x, y, z])
LAUNCH_POSITION = [0.0, 0.0, 460]

TARGET_COLUMNS = ['x', 'y', 'z']
EXCLUDED_COLUMNS = ['delay', 'rocket_id', 'simulation_id']
CATEGORICAL_COLUMN = ['motor_name', 'fin_cat', 'trigger']

def check_coordinate_system(training_csv_path='your_training_data.csv'):
    """
    Check if training data used a different coordinate convention
    """
    print("\n" + "="*60)
    print("COORDINATE SYSTEM DIAGNOSTIC")
    print("="*60)
    
    try:
        # Load a sample from training data
        train_df = pd.read_csv(training_csv_path)
        
        print(f"\nTraining data loaded: {len(train_df)} rows")
        print(f"Columns: {train_df.columns.tolist()}")
        
        # Check trajectories with heading=0 (should move primarily in one direction)
        if 'heading' in train_df.columns:
            heading_0 = train_df[train_df['heading'] == 0]
            
            if len(heading_0) > 0:
                sim_sample = heading_0[heading_0['simulation_id'] == heading_0['simulation_id'].iloc[0]]
                
                print("\nFor heading=0° trajectory:")
                print(f"  X range: {sim_sample['x'].min():.1f} to {sim_sample['x'].max():.1f}")
                print(f"  Y range: {sim_sample['y'].min():.1f} to {sim_sample['y'].max():.1f}")
                print(f"  Z range: {sim_sample['z'].min():.1f} to {sim_sample['z'].max():.1f}")
                
                print("\nExpected for heading=0°:")
                print("  X should be near 0 (no East-West drift)")
                print("  Y should show significant drift (North-South)")
                
                # Check actual drift direction
                final_x = sim_sample['x'].iloc[-1]
                final_y = sim_sample['y'].iloc[-1]
                drift_angle = np.degrees(np.arctan2(final_y, final_x))
                
                print(f"\nActual drift direction: {drift_angle:.1f}° from +X axis")
                print(f"Expected for heading=0°: 90° (pure +Y)")
                
                if abs(drift_angle - 90) > 20:
                    print("\n⚠️  WARNING: Training data may use different coordinate system!")
                    print("   Consider checking how heading was defined during training.")
            else:
                print("\nNo heading=0° trajectories found in training data")
        
        # Check wind columns
        wind_cols = [col for col in train_df.columns if 'wind' in col.lower()]
        print(f"\nWind-related columns: {wind_cols}")
        
        if wind_cols:
            print("\nWind statistics from training data:")
            print(train_df[wind_cols].describe())
        
    except Exception as e:
        print(f"Could not load training data: {e}")
        print("Skipping coordinate system check")
    
    print("="*60)

def detailed_diagnostics(user_inputs, sim_traj, ml_pred):
    """Comprehensive diagnostics for trajectory comparison"""
    
    # Convert ml_pred to numpy array if it's a list
    ml_pred = np.array(ml_pred)
    
    print("\n" + "="*70)
    print("DETAILED TRAJECTORY DIAGNOSTICS")
    print("="*70)
    
    # 1. Input Parameters
    print("\n1. INPUT PARAMETERS:")
    print(f"   Heading: {user_inputs['heading']}°")
    print(f"   Ramp Inclination: {user_inputs['ramp_inclinaison']}°")
    print(f"   Wind X: {user_inputs.get('wind_velocity_x', 'N/A')} m/s")
    print(f"   Wind Y: {user_inputs.get('wind_velocity_y', 'N/A')} m/s")
    
    # 2. Trajectory Statistics
    print("\n2. TRAJECTORY STATISTICS:")
    
    # Horizontal displacement
    sim_horiz_dist = np.sqrt(sim_traj[-1, 0]**2 + sim_traj[-1, 1]**2)
    ml_horiz_dist = np.sqrt(ml_pred[-1, 0]**2 + ml_pred[-1, 1]**2)
    
    print(f"   Final Horizontal Distance from Launch:")
    print(f"     RocketPy: {sim_horiz_dist:.1f} m")
    print(f"     ML:       {ml_horiz_dist:.1f} m")
    print(f"     Ratio:    {ml_horiz_dist/sim_horiz_dist:.2f}x")
    
    # Direction of drift
    sim_angle = np.degrees(np.arctan2(sim_traj[-1, 1], sim_traj[-1, 0]))
    ml_angle = np.degrees(np.arctan2(ml_pred[-1, 1], ml_pred[-1, 0]))
    
    print(f"\n   Drift Direction (from +X axis):")
    print(f"     RocketPy: {sim_angle:.1f}°")
    print(f"     ML:       {ml_angle:.1f}°")
    print(f"     Difference: {abs(sim_angle - ml_angle):.1f}°")
    
    # 3. Check different flight phases
    print("\n3. FLIGHT PHASE COMPARISON:")
    
    # Apogee indices
    sim_apogee_idx = np.argmax(sim_traj[:, 2])
    ml_apogee_idx = np.argmax(ml_pred[:, 2])
    
    phases = {
        '25% to apogee': 0.25,
        '50% to apogee': 0.50,
        '75% to apogee': 0.75,
        'At apogee': 1.0
    }
    
    for phase_name, fraction in phases.items():
        sim_idx = int(sim_apogee_idx * fraction)
        ml_idx = int(ml_apogee_idx * fraction)
        
        sim_pt = sim_traj[sim_idx]
        ml_pt = ml_pred[ml_idx]
        
        horiz_error = np.sqrt((sim_pt[0] - ml_pt[0])**2 + (sim_pt[1] - ml_pt[1])**2)
        vert_error = abs(sim_pt[2] - ml_pt[2])
        
        print(f"\n   {phase_name}:")
        print(f"     Horizontal error: {horiz_error:.1f} m")
        print(f"     Vertical error:   {vert_error:.1f} m")
    
    # 4. Velocity analysis at key points
    print("\n4. VELOCITY ANALYSIS:")
    
    # Estimate velocities from position differences
    dt_sim = sim_traj[1:] - sim_traj[:-1]
    dt_ml = ml_pred[1:] - ml_pred[:-1]
    
    # At 10% of flight
    idx_10_sim = len(sim_traj) // 10
    idx_10_ml = len(ml_pred) // 10
    
    vel_sim = dt_sim[idx_10_sim]
    vel_ml = dt_ml[idx_10_ml]
    
    print(f"   At 10% of flight:")
    print(f"     RocketPy velocity: ({vel_sim[0]:.2f}, {vel_sim[1]:.2f}, {vel_sim[2]:.2f}) m/step")
    print(f"     ML velocity:       ({vel_ml[0]:.2f}, {vel_ml[1]:.2f}, {vel_ml[2]:.2f}) m/step")
    
    print("\n" + "="*70)

def run_rocketpy_simulation(user_inputs, launch_position):
    """
    Run RocketCreator physics simulation with constant wind.
    
    Args:
        user_inputs (dict): User input parameters
        launch_position (list): Launch position [x, y, z]
        
    Returns:
        tuple: (trajectory_array, time_array) where trajectory is shape (N, 3) for [x, y, z]
    """
    print("\n" + "="*60)
    print("Running RocketCreator Physics Simulation...")
    print("="*60)
    
    try:
        # Map USER_INPUTS to RocketCreator parameters
        rocket_params = {
            'delay': 0,  # Not used when custom wind is provided
            'motor_name': user_inputs['motor_name'],
            'fin_cat': user_inputs['fin_cat'],
            'trigger': user_inputs['trigger'],
            'heading': user_inputs['heading'],
            'ramp_inclinaison': user_inputs['ramp_inclinaison'],
            'radius': user_inputs['radius'],
            'mass': user_inputs['mass'],
            'inertia': (user_inputs['ix'], user_inputs['iy'], user_inputs['iz']),
            'center_of_mass_without_motor': user_inputs['center_of_mass_without_motor'],
            'cone_length': user_inputs['cone_length'],
            'rocket_length': user_inputs['rocket_length'],
            'number_of_ailerons': user_inputs['number_of_ailerons'],
            'root_chord': user_inputs['root_chord'],
            'tip_chord': user_inputs['tip_chord'],
            'span': user_inputs['span'],
            'fins_pos': user_inputs['fins_pos'],
            'fin_inclinaison': user_inputs['fin_inclinaison'],
            'drag_coeff': user_inputs['drag_coeff'],
            'wind_velocity_x': user_inputs.get('wind_velocity_x'),
            'wind_velocity_y': user_inputs.get('wind_velocity_y'),
        }
        
        # Create rocket with constant wind
        if user_inputs.get('wind_velocity_x') is not None and user_inputs.get('wind_velocity_y') is not None:
            print(f"Using CONSTANT wind: X={user_inputs['wind_velocity_x']:.2f} m/s, Y={user_inputs['wind_velocity_y']:.2f} m/s")
        else:
            print("Using atmospheric forecast")
            
        rocket = RocketCreator(**rocket_params)
        
        # VERIFY: Check if wind is actually constant
        print("\n" + "="*40)
        print("WIND VERIFICATION")
        print("="*40)
        test_altitudes = [0, 500, 1000, 1500, 2000]
        wind_values = []
        for alt in test_altitudes:
            wind = rocket.get_wind_at_altitude(alt)
            wind_values.append(wind)
            print(f"Wind at {alt:4d}m: X={wind[0]:6.2f}, Y={wind[1]:6.2f} m/s")
        
        # Check if wind is actually constant
        wind_x_vals = [w[0] for w in wind_values]
        wind_y_vals = [w[1] for w in wind_values]
        
        if max(wind_x_vals) - min(wind_x_vals) < 0.1 and max(wind_y_vals) - min(wind_y_vals) < 0.1:
            print("[OK] Wind is CONSTANT across all altitudes")
        else:
            print("[WARNING] Wind is NOT constant - varies with altitude!")
            print("   This may cause mismatch with ML model if it was trained on constant wind")
        print("="*40 + "\n")
        
        # Extract trajectory data from Flight object
        flight = rocket.flight
        t_data = flight.time
        
        # Helper function to extract data
        def get_col(name, ref_len):
            val = getattr(flight, name, None)
            if val is None: 
                return np.zeros(ref_len)
            if callable(val):
                return val(t_data)
            elif isinstance(val, np.ndarray):
                return val
            else:
                return np.full(ref_len, val)
        
        # Extract x, y, z coordinates
        x_sim = get_col('x', len(t_data))
        y_sim = get_col('y', len(t_data))
        z_sim = get_col('z', len(t_data))
        
        # Combine into trajectory array
        trajectory = np.column_stack([x_sim, y_sim, z_sim])
        
        print(f"Simulation completed successfully!")
        print(f"Duration: {t_data[-1]:.2f} seconds")
        print(f"Data points: {len(t_data)}")
        print(f"Max Altitude: {np.max(z_sim):.2f} m")
        
        return trajectory, t_data
        
    except Exception as e:
        print(f"RocketCreator simulation failed: {e}")
        import traceback
        traceback.print_exc()
        return None, None

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
    df = df.copy()
    df['vx'] = df['x'].diff().fillna(0)
    df['vy'] = df['y'].diff().fillna(0)
    df['vz'] = df['z'].diff().fillna(0)
    
    # Smooth Velocity (Window 3) to prevent feedback loops in autoregression
    for col in ['vx', 'vy', 'vz']:
        df[col] = df[col].rolling(window=3, min_periods=1).mean()

    # Calculate Acceleration (Second Derivative)
    df['ax'] = df['vx'].diff().fillna(0)
    df['ay'] = df['vy'].diff().fillna(0)
    df['az'] = df['vz'].diff().fillna(0)
    
    # Smooth Acceleration
    for col in ['ax', 'ay', 'az']:
        df[col] = df[col].rolling(window=3, min_periods=1).mean()

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
    X_df = X_df.loc[:, ~X_df.columns.duplicated()]

    # --- Column Alignment ---
    if hasattr(x_scaler, 'feature_names_in_'):
        target_features = x_scaler.feature_names_in_
    else:
        target_features = feature_columns

    # 1. Add missing columns with 0
    for col in target_features:
        if col not in X_df.columns:
            X_df[col] = 0
            
    # 2. Select only relevant columns in the correct order
    X_df = X_df[target_features]
    
    return X_df

def plot_trajectory(y_pred, dt):
    print("Plotting trajectory...")
    y_pred_np = np.array(y_pred)
    
    # Calculate time array in seconds
    time_array = np.arange(len(y_pred_np)) * dt
    
    # Find max altitude and its index
    max_alt_idx = np.argmax(y_pred_np[:, 2])
    max_alt = y_pred_np[max_alt_idx, 2]
    max_alt_time = time_array[max_alt_idx]
    max_alt_pos = y_pred_np[max_alt_idx]
    
    print(f"Max Altitude: {max_alt:.2f} m at t={max_alt_time:.2f}s")

    # --- Plot 1: 3D Trajectory ---
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')

    # Plot Predicted Path
    ax.plot(y_pred_np[:, 0], y_pred_np[:, 1], y_pred_np[:, 2],
            label='Predicted Trajectory', color='red', linestyle='--', linewidth=2, alpha=0.7)
    
    # Mark max altitude point
    ax.scatter([max_alt_pos[0]], [max_alt_pos[1]], [max_alt_pos[2]], 
               color='gold', s=200, marker='*', edgecolors='black', linewidth=1.5,
               label=f'Max Altitude ({max_alt:.1f}m)', zorder=5)

    ax.set_title('3D Flight Trajectory Prediction')
    ax.set_xlabel('X Position (m)')
    ax.set_ylabel('Y Position (m)')
    ax.set_zlabel('Z Position (m)')
    ax.legend()
    
    output_file_3d = "trajectory_prediction_plot_3d.png"
    plt.savefig(output_file_3d)
    print(f"3D Plot saved to {output_file_3d}")
    plt.close()

    # --- Plot 2: 2D Component Breakdown (X, Y, Z vs Time) ---
    fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
    
    components = ['X', 'Y', 'Z']
    colors = ['blue', 'orange', 'purple']
    
    for i in range(3):
        axes[i].plot(time_array, y_pred_np[:, i], label=f'Predicted {components[i]}', 
                     color=colors[i], linestyle='--', linewidth=1.5)
        axes[i].set_ylabel(f'{components[i]} Position (m)', fontsize=11)
        axes[i].legend(loc='upper right')
        axes[i].grid(True, alpha=0.3)
        
        # Mark max altitude on Z plot
        if i == 2:  # Z component
            axes[i].scatter([max_alt_time], [max_alt], 
                          color='gold', s=150, marker='*', edgecolors='black', 
                          linewidth=1.5, label=f'Apogee ({max_alt:.1f}m at {max_alt_time:.1f}s)', zorder=5)
            axes[i].legend(loc='upper right')
    
    plt.xlabel('Time (seconds)', fontsize=11)
    plt.suptitle('Coordinate-wise Prediction (X, Y, Z vs Time)', fontsize=13, fontweight='bold')
    plt.tight_layout()
    
    output_file_2d = "trajectory_prediction_plot_2d.png"
    plt.savefig(output_file_2d)
    print(f"2D Plot saved to {output_file_2d}")
    plt.close()

def plot_comparison(ml_pred, ml_time, sim_traj, sim_time, dt, heading, save_plots=True, show_plots=False):
    """
    Create comparison plots between ML prediction and RocketCreator simulation.
    """
    print("\nCreating comparison plots...")
    
    ml_pred_np = np.array(ml_pred)
    
    # Diagnostic: Analyze coordinate differences
    print("\n" + "="*60)
    print("COORDINATE DIAGNOSTIC")
    print("="*60)
    print(f"ML X - Range: [{np.min(ml_pred_np[:, 0]):.2f}, {np.max(ml_pred_np[:, 0]):.2f}] m")
    print(f"RocketPy X - Range: [{np.min(sim_traj[:, 0]):.2f}, {np.max(sim_traj[:, 0]):.2f}] m")
    print(f"ML Y - Range: [{np.min(ml_pred_np[:, 1]):.2f}, {np.max(ml_pred_np[:, 1]):.2f}] m")
    print(f"RocketPy Y - Range: [{np.min(sim_traj[:, 1]):.2f}, {np.max(sim_traj[:, 1]):.2f}] m")
    print(f"ML Z - Range: [{np.min(ml_pred_np[:, 2]):.2f}, {np.max(ml_pred_np[:, 2]):.2f}] m")
    print(f"RocketPy Z - Range: [{np.min(sim_traj[:, 2]):.2f}, {np.max(sim_traj[:, 2]):.2f}] m")
    print("="*60 + "\n")
    
    # Both ML and RocketPy use Earth frame coordinates (X=East, Y=North, Z=Altitude)
    # No artificial corrections needed - model should match simulation directly
    ml_pred_corrected = ml_pred_np.copy()
    
    # Find max altitudes
    ml_max_idx = np.argmax(ml_pred_corrected[:, 2])
    ml_max_alt = ml_pred_corrected[ml_max_idx, 2]
    ml_max_time = ml_time[ml_max_idx]
    ml_max_pos = ml_pred_corrected[ml_max_idx]
    
    sim_max_idx = np.argmax(sim_traj[:, 2])
    sim_max_alt = sim_traj[sim_max_idx, 2]
    sim_max_time = sim_time[sim_max_idx]
    sim_max_pos = sim_traj[sim_max_idx]
    
    print(f"\nML Prediction - Max Altitude: {ml_max_alt:.2f} m at t={ml_max_time:.2f}s")
    print(f"RocketPy Simulation - Max Altitude: {sim_max_alt:.2f} m at t={sim_max_time:.2f}s")
    print(f"Difference: {abs(ml_max_alt - sim_max_alt):.2f} m ({abs(ml_max_alt - sim_max_alt)/sim_max_alt*100:.1f}%)")
    
    # --- Plot 1: 3D Trajectory Comparison ---
    fig = plt.figure(figsize=(12, 9))
    ax = fig.add_subplot(111, projection='3d')
    
    # Plot RocketPy Simulation (Blue solid line)
    ax.plot(sim_traj[:, 0], sim_traj[:, 1], sim_traj[:, 2],
            label='RocketPy Simulation', color='blue', linestyle='-', linewidth=2.5, alpha=0.8)
    
    # Plot ML Prediction (Red dashed line)
    ax.plot(ml_pred_corrected[:, 0], ml_pred_corrected[:, 1], ml_pred_corrected[:, 2],
            label='ML Prediction', color='red', linestyle='--', linewidth=2, alpha=0.7)
    
    # Mark max altitude points
    ax.scatter([sim_max_pos[0]], [sim_max_pos[1]], [sim_max_pos[2]], 
               color='blue', s=200, marker='*', edgecolors='black', linewidth=1.5,
               label=f'RocketPy Apogee ({sim_max_alt:.1f}m)', zorder=5)
    
    ax.scatter([ml_max_pos[0]], [ml_max_pos[1]], [ml_max_pos[2]], 
               color='red', s=200, marker='*', edgecolors='black', linewidth=1.5,
               label=f'ML Apogee ({ml_max_alt:.1f}m)', zorder=5)
    
    ax.set_title('3D Flight Trajectory Comparison\nRocketPy Physics vs ML Prediction', 
                 fontsize=14, fontweight='bold')
    ax.set_xlabel('X Position (m)', fontsize=11)
    ax.set_ylabel('Y Position (m)', fontsize=11)
    ax.set_zlabel('Z Position (m)', fontsize=11)
    ax.legend(loc='upper left', fontsize=10)
    ax.grid(True, alpha=0.3)
    
    if save_plots:
        output_file_3d = "trajectory_comparison_3d.png"
        plt.savefig(output_file_3d, dpi=150)
        print(f"3D Comparison Plot saved to {output_file_3d}")
    
    if show_plots:
        plt.show()
    else:
        plt.close()
    
    # --- Plot 2: 2D Component Comparison (X, Y, Z vs Time) ---
    fig, axes = plt.subplots(3, 1, figsize=(14, 11), sharex=True)
    
    components = ['X', 'Y', 'Z']
    colors_sim = ['#1f77b4', '#1f77b4', '#1f77b4']  # Blues
    colors_ml = ['#d62728', '#d62728', '#d62728']   # Reds
    
    for i in range(3):
        # Plot RocketPy Simulation
        axes[i].plot(sim_time, sim_traj[:, i], 
                     label=f'RocketPy {components[i]}', 
                     color=colors_sim[i], linestyle='-', linewidth=2.5, alpha=0.8)
        
        # Plot ML Prediction
        axes[i].plot(ml_time, ml_pred_corrected[:, i], 
                     label=f'ML {components[i]}', 
                     color=colors_ml[i], linestyle='--', linewidth=2, alpha=0.7)
        
        axes[i].set_ylabel(f'{components[i]} Position (m)', fontsize=12, fontweight='bold')
        axes[i].legend(loc='upper right', fontsize=10)
        axes[i].grid(True, alpha=0.3)
        
        # Mark max altitude on Z plot
        if i == 2:  # Z component
            axes[i].scatter([sim_max_time], [sim_max_alt], 
                          color='blue', s=150, marker='*', edgecolors='black', 
                          linewidth=1.5, zorder=5)
            axes[i].scatter([ml_max_time], [ml_max_alt], 
                          color='red', s=150, marker='*', edgecolors='black', 
                          linewidth=1.5, zorder=5)
            
            # Add text annotations for apogee values
            axes[i].annotate(f'RocketPy: {sim_max_alt:.1f}m', 
                           xy=(sim_max_time, sim_max_alt), 
                           xytext=(10, 20), textcoords='offset points',
                           bbox=dict(boxstyle='round,pad=0.5', fc='lightyellow', alpha=0.8),
                           arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))
            
            axes[i].annotate(f'ML: {ml_max_alt:.1f}m', 
                           xy=(ml_max_time, ml_max_alt), 
                           xytext=(10, -30), textcoords='offset points',
                           bbox=dict(boxstyle='round,pad=0.5', fc='lightcoral', alpha=0.8),
                           arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))
    
    plt.xlabel('Time (seconds)', fontsize=12, fontweight='bold')
    plt.suptitle('Trajectory Component Comparison (X, Y, Z vs Time)\nRocketPy Physics vs ML Prediction', 
                 fontsize=14, fontweight='bold')
    plt.tight_layout()
    
    if save_plots:
        output_file_2d = "trajectory_comparison_2d.png"
        plt.savefig(output_file_2d, dpi=150)
        print(f"2D Comparison Plot saved to {output_file_2d}")
    
    if show_plots:
        plt.show()
    else:
        plt.close()

def export_to_kml(y_pred, filename="trajectory.kml"):
    print(f"Exporting to {filename}...")
    
    # Launch Site Coordinates
    LAT0 = 43.218436
    LON0 = 0.047333
    
    meters_to_lat = 1.0 / 111111.0
    meters_to_lon = 1.0 / (111111.0 * math.cos(math.radians(LAT0)))
    
    def format_coords(data):
        coords_str = ""
        for point in data:
            x, y, z = point
            
            check_lon = LON0 + (x * meters_to_lon)
            check_lat = LAT0 + (y * meters_to_lat)
            check_alt = z 
            
            coords_str += f"{check_lon},{check_lat},{check_alt} "
        return coords_str.strip()

    kml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Rocket Trajectory</name>
    <Style id="predStyle">
      <LineStyle>
        <color>ff0000ff</color> <!-- Red -->
        <width>2</width>
      </LineStyle>
    </Style>
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
    # Check training data coordinate system (optional diagnostic)
    # Uncomment if you have training data CSV available
    # check_coordinate_system('path_to_training_data.csv')
    
    model, x_scaler, y_scaler, feature_columns = load_artifacts()

    print("\n" + "="*60)
    print("INITIALIZING ROCKET TRAJECTORY PREDICTION")
    print("="*60)
    print(f"Inputs: {USER_INPUTS}")
    print(f"Launch Position: {LAUNCH_POSITION}")
    print(f"History window: {HISTORY_TIME}s ({N_STEPS} steps)")
    print(f"Prediction duration: {PREDICTION_TIME}s ({PREDICTION_STEPS} steps)")
    print("="*60)

    # --- Time Configuration ---
    DT = 0.01  # 10ms time step

    # 1. Initialize History Buffer
    initial_data = []
    
    # Create the initial DataFrame structure
    # IMPORTANT: Convert heading from degrees to radians for model compatibility
    base_row = {
        'x': LAUNCH_POSITION[0],
        'y': LAUNCH_POSITION[1],
        'z': LAUNCH_POSITION[2],
        **USER_INPUTS,
        'delay': 0, 
        'rocket_id': 0, 
        'simulation_id': 0 
    }
    
    # Keep heading in degrees (training data uses degrees, not radians)
    base_row['heading'] = USER_INPUTS['heading']
    print(f"\nUsing heading: {USER_INPUTS['heading']}° (degrees, as in training data)")

    # Populate history with T = -N*dt ... -dt
    # This represents the rocket sitting on the pad before launch
    for i in range(N_STEPS):
        row = base_row.copy()
        t = (i - N_STEPS) * DT
        row['time'] = t
        initial_data.append(row)
        
    history_df = pd.DataFrame(initial_data)

    # Initialize predictions with launch position history
    predictions = [LAUNCH_POSITION] * N_STEPS
    
    print(f"\nStarting ML prediction for {PREDICTION_STEPS} steps...")
    
    # Prepare all prediction data at once
    all_histories = []
    current_time = 0.0
    current_history_df = history_df.copy()
    
    # Generate all predictions in batch
    for step in tqdm(range(PREDICTION_STEPS), desc="Preparing sequences", colour='blue'):
        # Preprocess current history
        X_processed_df = preprocess_input(current_history_df, feature_columns, x_scaler)
        X_scaled = x_scaler.transform(X_processed_df.values)
        
        # Create sequence from last N_STEPS
        if len(X_scaled) < N_STEPS:
            print("Error: History buffer too small.")
            break
        
        current_sequence = X_scaled[-N_STEPS:]
        all_histories.append(current_sequence)
        
        # Update time
        current_time += DT
        
        # Create next state for history (will be updated with prediction)
        new_row = base_row.copy()
        new_row['time'] = current_time
        
        # Add temporary placeholder (will update after batch prediction)
        new_row_df = pd.DataFrame([new_row])
        current_history_df = pd.concat([current_history_df, new_row_df], ignore_index=True)
        
        # Keep history buffer manageable
        if len(current_history_df) > N_STEPS + 20:
            current_history_df = current_history_df.iloc[-(N_STEPS + 20):]
    
    # Batch predict all at once
    print(f"Running batch prediction on {len(all_histories)} sequences...")
    all_sequences = np.array(all_histories)  # Shape: (PREDICTION_STEPS, N_STEPS, features)
    y_pred_scaled_batch = model.predict(all_sequences, verbose=1)
    y_pred_batch = y_scaler.inverse_transform(y_pred_scaled_batch)
    
    # Update predictions with actual predicted values
    predictions.extend(y_pred_batch.tolist())
    
    print("ML Prediction complete.")

    # Statistics
    predictions_np = np.array(predictions)
    max_alt = np.max(predictions_np[:, 2])
    final_time = current_time
    
    print("\n" + "="*60)
    print("ML PREDICTION STATISTICS")
    print("="*60)
    print(f"Duration: {final_time:.2f} s")
    print(f"Total steps: {len(predictions)}")
    print(f"Max Altitude (Z): {max_alt:.2f} m")
    print(f"Final Position: ({predictions[-1][0]:.1f}, {predictions[-1][1]:.1f}, {predictions[-1][2]:.1f}) m")
    print("="*60)
    
    # Run RocketPy simulation for comparison
    sim_trajectory, sim_time = run_rocketpy_simulation(USER_INPUTS, LAUNCH_POSITION)
    
    # Visualizations
    print("\n" + "="*60)
    print("GENERATING VISUALIZATIONS")
    print("="*60)
    
    plot_trajectory(predictions, DT)
    export_to_kml(predictions)
    
    # Comparison plots (if simulation succeeded)
    if sim_trajectory is not None and sim_time is not None:
        # Create time array for ML predictions
        ml_time = np.arange(len(predictions)) * DT
        plot_comparison(predictions, ml_time, sim_trajectory, sim_time, DT, USER_INPUTS['heading'])
        
        # Detailed diagnostics
        detailed_diagnostics(USER_INPUTS, sim_trajectory, predictions)
        
        print("\n" + "="*60)
        print("✓ COMPARISON COMPLETE!")
        print("="*60)
        print("\nGenerated files:")
        print("  - trajectory_prediction_plot_3d.png")
        print("  - trajectory_prediction_plot_2d.png")
        print("  - trajectory_comparison_3d.png")
        print("  - trajectory_comparison_2d.png")
        print("  - trajectory.kml")
        print("\nCheck the console output above for detailed diagnostics.")
        print("="*60)
    else:
        print("\n[WARNING] Skipping comparison plots due to simulation failure.")
        print("Check RocketCreator configuration and wind settings.")

if __name__ == "__main__":
    main()