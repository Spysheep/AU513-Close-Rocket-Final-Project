import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import tensorflow as tf
from tensorflow.keras import layers, models, callbacks

# --- GPU Configuration ---
gpus = tf.config.list_physical_devices('GPU')
if gpus:
    try:
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
        logical_gpus = tf.config.list_logical_devices('GPU')
        print(len(gpus), "Physical GPUs,", len(logical_gpus), "Logical GPUs")
    except RuntimeError as e:
        print(e)
else:
    print("No GPU detected. Running on CPU.")

# --- 1. Configuration Parameters ---
FILE_PATH = 'dataset_tensorflow_optimized.csv'
N_STEPS = 30
TEST_SIZE = 0.2
BATCH_SIZE = 512
EPOCHS = 50
LEARNING_RATE = 0.001

# Target columns are x, y, z
TARGET_COLUMNS = ['x', 'y', 'z']
# Input is everything else except delay
EXCLUDED_COLUMNS = ['delay']

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

# --- 3. Data Loading and Preparation ---
print("--- Data Loading and Preparation ---")
try:
    df = pd.read_csv(FILE_PATH)
except FileNotFoundError:
    print(f"Error: File not found at {FILE_PATH}.")
    exit()

# Drop excluded columns
df = df.drop(columns=EXCLUDED_COLUMNS, errors='ignore')

# Separate Features (X) and Target (Y)
# Y is x, y, z
Y_df = df[TARGET_COLUMNS]

# X is everything else. 
X_df = df

print(f"Input features: {X_df.columns.tolist()}")
print(f"Target features: {Y_df.columns.tolist()}")

# --- 4. Scaling ---
x_scaler = StandardScaler()
y_scaler = StandardScaler()

X_scaled = x_scaler.fit_transform(X_df)
Y_scaled = y_scaler.fit_transform(Y_df)

X_scaled_df = pd.DataFrame(X_scaled, columns=X_df.columns)
Y_scaled_df = pd.DataFrame(Y_scaled, columns=Y_df.columns)

# --- 5. Split Data ---
# Shuffle=False is important for time series if we want to test on the "future"
train_index, test_index = train_test_split(X_scaled_df.index, test_size=TEST_SIZE, shuffle=False)

X_train_flat = X_scaled_df.iloc[train_index]
Y_train_flat = Y_scaled_df.iloc[train_index]
X_test_flat = X_scaled_df.iloc[test_index]
Y_test_flat = Y_scaled_df.iloc[test_index]

# --- 6. Sequence Generation ---
X_train_seq, Y_train_seq = create_sequences(X_train_flat, Y_train_flat, N_STEPS)
X_test_seq, Y_test_seq = create_sequences(X_test_flat, Y_test_flat, N_STEPS)

N_FEATURES = X_train_seq.shape[2]
N_OUTPUTS = Y_train_seq.shape[1]
print(f"Input shape: {X_train_seq.shape}")
print(f"Output shape: {Y_train_seq.shape}")

# --- 7. Transformer Model Definition ---
def transformer_encoder(inputs, head_size, num_heads, ff_dim, dropout=0):
    # Normalization and Attention
    x = layers.LayerNormalization(epsilon=1e-6)(inputs)
    x = layers.MultiHeadAttention(
        key_dim=head_size, num_heads=num_heads, dropout=dropout
    )(x, x)
    x = layers.Dropout(dropout)(x)
    res = x + inputs

    # Feed Forward Part
    x = layers.LayerNormalization(epsilon=1e-6)(res)
    x = layers.Conv1D(filters=ff_dim, kernel_size=1, activation="relu")(x)
    x = layers.Dropout(dropout)(x)
    x = layers.Conv1D(filters=inputs.shape[-1], kernel_size=1)(x)
    return x + res

def build_model(input_shape, head_size, num_heads, ff_dim, num_transformer_blocks, mlp_units, dropout=0, mlp_dropout=0):
    inputs = layers.Input(shape=input_shape)
    x = inputs
    for _ in range(num_transformer_blocks):
        x = transformer_encoder(x, head_size, num_heads, ff_dim, dropout)

    x = layers.GlobalAveragePooling1D()(x)
    for dim in mlp_units:
        x = layers.Dense(dim, activation="relu")(x)
        x = layers.Dropout(mlp_dropout)(x)
    
    outputs = layers.Dense(N_OUTPUTS)(x) # Linear activation for regression
    return models.Model(inputs, outputs)

print("\n--- Model Definition ---")
input_shape = (N_STEPS, N_FEATURES)

model = build_model(
    input_shape=input_shape,
    head_size=256,
    num_heads=4,
    ff_dim=4,
    num_transformer_blocks=4,
    mlp_units=[128],
    dropout=0.25,
    mlp_dropout=0.25
)

optimizer = tf.keras.optimizers.Adam(learning_rate=LEARNING_RATE)
model.compile(optimizer=optimizer, loss='mse', metrics=['mae'])
model.summary()

# --- 8. Training ---
reduce_lr = callbacks.ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=5, min_lr=1e-6)
early_stopping = callbacks.EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True)

print(f"\nTraining model for {EPOCHS} epochs...")
history = model.fit(
    X_train_seq,
    Y_train_seq,
    epochs=EPOCHS,
    batch_size=BATCH_SIZE,
    validation_split=0.1,
    verbose=1,
    callbacks=[reduce_lr, early_stopping]
)

# --- 9. Evaluation ---
print("\n--- Evaluation ---")
test_loss, test_mae = model.evaluate(X_test_seq, Y_test_seq, verbose=0)
print(f"Test Loss (MSE): {test_loss:.4f}")
print(f"Test MAE: {test_mae:.4f}")

# Predictions
y_pred_scaled = model.predict(X_test_seq)
y_pred = y_scaler.inverse_transform(y_pred_scaled)
y_true = y_scaler.inverse_transform(Y_test_seq)

# --- 10. Visualization ---
print("\n--- Plotting Results ---")

# History
plt.figure(figsize=(12, 5))
plt.subplot(1, 2, 1)
plt.plot(history.history['loss'], label='Train Loss')
plt.plot(history.history['val_loss'], label='Val Loss')
plt.title('Model Loss (MSE)')
plt.xlabel('Epoch')
plt.ylabel('Loss')
plt.legend()

plt.subplot(1, 2, 2)
plt.plot(history.history['mae'], label='Train MAE')
plt.plot(history.history['val_mae'], label='Val MAE')
plt.title('Model MAE')
plt.xlabel('Epoch')
plt.ylabel('MAE')
plt.legend()
plt.tight_layout()
plt.show()

# 3D Trajectory
fig = plt.figure(figsize=(10, 8))
ax = fig.add_subplot(111, projection='3d')
ax.plot(y_true[:, 0], y_true[:, 1], y_true[:, 2], label='Actual', color='green', alpha=0.7)
ax.plot(y_pred[:, 0], y_pred[:, 1], y_pred[:, 2], label='Predicted', color='red', linestyle='--', alpha=0.7)
ax.set_title('3D Trajectory Prediction')
ax.set_xlabel('X')
ax.set_ylabel('Y')
ax.set_zlabel('Z')
ax.legend()
plt.show()

# --- 11. Save Model ---
model.save("models/transformer_trajectory_model.keras")
print("Model saved to models/transformer_trajectory_model.keras")