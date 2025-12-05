import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from tf_keras.models import Sequential
from tf_keras.layers import LSTM, Dense, Dropout, BatchNormalization
from tf_keras.optimizers import Adam
from tf_keras.callbacks import ReduceLROnPlateau
from tf_keras.regularizers import l2
import tensorflow as tf
import tf2onnx
import subprocess
import os
import shutil

# --- 1. Configuration Parameters ---
FILE_PATH = 'dataset_tensorflow.csv'
N_STEPS = 30
TEST_SIZE = 0.2
BATCH_SIZE = 512
EPOCHS = 50

TARGET_COLUMNS = ['x', 'y', 'z']
EXCLUDED_COLUMNS = ['delay', 'rocket_id', 'simulation_id']
CATEGORICAL_COLUMN = ['motor_name', 'fin_cat', 'trigger']


# --- 2. Sequence Creation Function ---
def create_sequences(X, Y, n_steps):
    X_data = X.values if isinstance(X, (pd.DataFrame, pd.Series)) else X
    Y_data = Y.values if isinstance(Y, (pd.DataFrame, pd.Series)) else Y
    X_seq, Y_seq = [], []
    for i in range(len(X_data) - n_steps):
        seq_x = X_data[i:i + n_steps]
        seq_y = Y_data[i + n_steps]
        X_seq.append(seq_x)
        Y_seq.append(seq_y)
    return np.array(X_seq), np.array(Y_seq)


# --- 3. Data Loading ---
print("--- Data Loading and Preparation ---")
try:
    df = pd.read_csv(FILE_PATH)
except FileNotFoundError:
    print(f"Error: File not found at {FILE_PATH}.")
    exit()

# --- NEW: Feature Engineering (Physics) ---
print("Generating Velocity and Acceleration features...")
# Calculate Velocity (First Derivative)
df['vx'] = df['x'].diff().fillna(0)
df['vy'] = df['y'].diff().fillna(0)
df['vz'] = df['z'].diff().fillna(0)

# Calculate Acceleration (Second Derivative) - Optional, helps if data is clean
df['ax'] = df['vx'].diff().fillna(0)
df['ay'] = df['vy'].diff().fillna(0)
df['az'] = df['vz'].diff().fillna(0)

# --- 4. Separation ---
# We keep the new physics columns in X, but Y is still just x,y,z
columns_to_drop = TARGET_COLUMNS + EXCLUDED_COLUMNS
X_df = df.drop(columns=columns_to_drop, axis=1, errors='ignore')
# Ensure our new features are INCLUDED in X_df
X_df = pd.concat([X_df, df[['vx', 'vy', 'vz', 'ax', 'ay', 'az']]], axis=1)

Y_df = df[TARGET_COLUMNS]

# One-Hot Encoding
present_categorical_cols = [col for col in CATEGORICAL_COLUMN if col in X_df.columns]
if present_categorical_cols:
    X_df = pd.get_dummies(X_df, columns=present_categorical_cols, drop_first=False)

# --- 5. Scaling (StandardScaler) ---
# StandardScaler is better for data that follows a normal distribution (like physics errors)
x_scaler = StandardScaler()
y_scaler = StandardScaler()

X_scaled = x_scaler.fit_transform(X_df)
Y_scaled = y_scaler.fit_transform(Y_df)
X_scaled_df = pd.DataFrame(X_scaled, columns=X_df.columns)
Y_scaled_df = pd.DataFrame(Y_scaled, columns=Y_df.columns)

# Split
train_index, test_index = train_test_split(X_scaled_df.index, test_size=TEST_SIZE, shuffle=False)
X_train_flat = X_scaled_df.iloc[train_index]
Y_train_flat = Y_scaled_df.iloc[train_index]
X_test_flat = X_scaled_df.iloc[test_index]
Y_test_flat = Y_scaled_df.iloc[test_index]

# Sequence Generation
X_train_seq, Y_train_seq = create_sequences(X_train_flat, Y_train_flat, N_STEPS)
X_test_seq, Y_test_seq = create_sequences(X_test_flat, Y_test_flat, N_STEPS)

N_FEATURES = X_train_seq.shape[2]
N_OUTPUTS = Y_train_seq.shape[1]
print(f"Features in input: {N_FEATURES} (Includes Velocity/Accel)")

# --- Model Definition and Training (OPTIMIZED) ---
print("\n--- Model Definition and Training ---")
input_shape = (N_STEPS, N_FEATURES)

model = Sequential([
    # Layer 1: Reduced units
    LSTM(units=64, input_shape=input_shape, return_sequences=True, kernel_regularizer=l2(0.01)),
    BatchNormalization(),
    Dropout(0.4),

    # Layer 2: Stacked LSTM
    LSTM(units=32, return_sequences=True, kernel_regularizer=l2(0.01)),
    BatchNormalization(),
    Dropout(0.4),

    # Layer 3: Final LSTM (return_sequences=False)
    LSTM(units=16, return_sequences=False, kernel_regularizer=l2(0.01)),
    BatchNormalization(),
    Dropout(0.4),

    # Dense Layers
    Dense(units=8, activation='relu', kernel_regularizer=l2(0.01)),
    Dense(units=N_OUTPUTS)  # Output layer (Linear activation is correct for regression)
])

# Use a slightly lower learning rate to stabilize training
optimizer = Adam(learning_rate=0.001)

model.compile(optimizer=optimizer, loss='mse', metrics=['mae'])
model.summary()

# Define the callback
reduce_lr = ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=5, min_lr=1e-6)

print(f"\nTraining model for {EPOCHS} epochs...")
history = model.fit(
    X_train_seq,
    Y_train_seq,
    epochs=EPOCHS,
    batch_size=BATCH_SIZE,
    validation_split=0.1,
    verbose=1,
    callbacks=[reduce_lr]
)

# Evaluation and Prediction
print("\n--- Evaluation ---")
test_loss, test_mae = model.evaluate(X_test_seq, Y_test_seq, verbose=0)
print(f"Test Loss (MSE): {test_loss:.4f}")
print(f"Test MAE (Mean Absolute Error): {test_mae:.4f}")

# Make predictions
y_pred_scaled = model.predict(X_test_seq)
y_pred = y_scaler.inverse_transform(y_pred_scaled)
y_true = y_scaler.inverse_transform(Y_test_seq)

print("\nFirst 5 Predicted (x, y, z):")
print(y_pred[:5])
print("\nFirst 5 Actual (x, y, z):")
print(y_true[:5])

import matplotlib.pyplot as plt

# --- 7. Plotting History ---

print("\n--- Plotting Training History ---")

# Access the logged metrics from the history object
train_loss = history.history['loss']
val_loss = history.history['val_loss']
train_mae = history.history['mae']
val_mae = history.history['val_mae']
epochs = range(1, len(train_loss) + 1)

# Plot 1: Loss (Mean Square Error)
plt.figure(figsize=(12, 5))
plt.subplot(1, 2, 1)
plt.plot(epochs, train_loss, 'b', label='Training Loss (MSE)')
plt.plot(epochs, val_loss, 'r', label='Validation Loss (MSE)')
plt.title('Training and Validation Loss')
plt.xlabel('Epochs')
plt.ylabel('Loss (MSE)')
plt.legend()

# Plot 2: MAE (Mean Absolute Error)
plt.subplot(1, 2, 2)
plt.plot(epochs, train_mae, 'b', label='Training MAE')
plt.plot(epochs, val_mae, 'r', label='Validation MAE')
plt.title('Training and Validation MAE')
plt.xlabel('Epochs')
plt.ylabel('MAE')
plt.legend()

plt.tight_layout()
plt.show()

# --- 8. Trajectory Visualization ---

print("\n--- Plotting Trajectory ---")

# Ensure y_true and y_pred are numpy arrays
y_true_np = np.array(y_true)
y_pred_np = np.array(y_pred)

# --- Plot 1: 3D Trajectory ---
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

plt.xlabel('Time Step (Test Set)')
plt.suptitle('Coordinate-wise Comparison (X, Y, Z)')
plt.tight_layout()
plt.show()

#
print("\nHistory plots generated for Loss (MSE) and MAE.")

# --- 9. Save Model ---
print("\n--- Saving Model ---")
model.save("models/trajectory_model.keras")