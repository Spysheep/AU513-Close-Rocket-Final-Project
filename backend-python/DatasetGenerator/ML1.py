import pandas as pd
import numpy as np
import ast
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout

# --- 1. Configuration Parameters ---
FILE_PATH = 'dataset_tensorflow.csv'
N_STEPS = 10
TEST_SIZE = 0.2
BATCH_SIZE = 64
EPOCHS = 50

# Define the columns based on your request and the errors
TARGET_COLUMNS = ['x', 'y', 'z']
EXCLUDED_COLUMNS = ['delay', 'rocket_id', 'simulation_id']

# Use the column names identified from your tracebacks and prints:
# This must be a list if you are processing multiple columns.
CATEGORICAL_COLUMN = ['motor_name','fin_cat','trigger']


# --- 2. Sequence Creation Function (Unchanged) ---
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
    print(f"Error: File not found at {FILE_PATH}. Please check the path.")
    exit()

# --- 5. Separation and Categorical Handling (FIXED) ---

# Combine all columns to be dropped from X
columns_to_drop = TARGET_COLUMNS + EXCLUDED_COLUMNS

# Separate Input Features (X) and Output Targets (Y)
X_df = df.drop(columns=columns_to_drop, axis=1, errors='ignore')
Y_df = df[TARGET_COLUMNS]

# Identify categorical columns actually present in X_df
present_categorical_cols = [col for col in CATEGORICAL_COLUMN if col in X_df.columns]

# Categorical Data Handling (One-Hot Encoding)
if present_categorical_cols:
    print(f"Applying One-Hot Encoding to columns: {present_categorical_cols}...")
    # Apply get_dummies to the list of present columns
    X_df = pd.get_dummies(X_df, columns=present_categorical_cols, drop_first=False)
else:
    print(f"Warning: None of the categorical columns {CATEGORICAL_COLUMN} were found in X_df.")

# --- 6. Scaling and Subsequent Steps ---
x_scaler = MinMaxScaler()
y_scaler = MinMaxScaler()

X_scaled = x_scaler.fit_transform(X_df)
Y_scaled = y_scaler.fit_transform(Y_df)
X_scaled_df = pd.DataFrame(X_scaled, columns=X_df.columns)
Y_scaled_df = pd.DataFrame(Y_scaled, columns=Y_df.columns)

# Train-Test Split (Sequential Split)
train_index, test_index = train_test_split(
    X_scaled_df.index, test_size=TEST_SIZE, shuffle=False
)
X_train_flat = X_scaled_df.iloc[train_index]
Y_train_flat = Y_scaled_df.iloc[train_index]
X_test_flat = X_scaled_df.iloc[test_index]
Y_test_flat = Y_scaled_df.iloc[test_index]
print(f"Training Samples: {len(X_train_flat)}, Testing Samples: {len(X_test_flat)}")

# Sequence Generation for LSTM
X_train_seq, Y_train_seq = create_sequences(X_train_flat, Y_train_flat, N_STEPS)
X_test_seq, Y_test_seq = create_sequences(X_test_flat, Y_test_flat, N_STEPS)
N_FEATURES = X_train_seq.shape[2]
N_OUTPUTS = Y_train_seq.shape[1]
print(f"Final LSTM Training Input Shape: {X_train_seq.shape}")

# Model Definition and Training
print("\n--- Model Definition and Training ---")
input_shape = (N_STEPS, N_FEATURES)
model = Sequential([
    # LSTM Layers (return_sequences=True for the first five)
    LSTM(units=512, activation='relu', input_shape=input_shape, return_sequences=True),
    Dropout(0.2),
    LSTM(units=256, activation='relu', return_sequences=True),
    Dropout(0.2),
    LSTM(units=128, activation='relu', return_sequences=True),
    Dropout(0.2),
    LSTM(units=64, activation='relu', return_sequences=True),
    Dropout(0.2),
    LSTM(units=32, activation='relu', return_sequences=True),
    Dropout(0.2),
    # Last LSTM layer (return_sequences=False to output a vector for the Dense layers)
    LSTM(units=16, activation='relu', return_sequences=False),
    Dropout(0.2),
    # Dense Layers for Transfer Learning preparation
    Dense(units=8, activation='relu'),
    # Final Dense Output Layer
    Dense(units=N_OUTPUTS)
])

model.compile(optimizer='adam', loss='mse', metrics=['mae'])
model.summary()

print(f"\nTraining model for {EPOCHS} epochs...")
history = model.fit(
    X_train_seq,
    Y_train_seq,
    epochs=EPOCHS,
    batch_size=BATCH_SIZE,
    validation_split=0.1,
    verbose=1
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

# Plot 1: Loss (Mean Squared Error)
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

#
print("\nHistory plots generated for Loss (MSE) and MAE.")