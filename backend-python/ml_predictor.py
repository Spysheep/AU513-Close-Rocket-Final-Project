"""
ML Predictor module for rocket trajectory prediction
Loads and uses the trained TensorFlow model
"""

import tensorflow as tf
import joblib
import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)

# Model paths
MODEL_PATH = 'models/trajectory_model.keras'
X_SCALER_PATH = 'models/x_scaler.save'
Y_SCALER_PATH = 'models/y_scaler.save'
FEATURE_COLUMNS_PATH = 'models/feature_columns.save'

# Time configuration
DT = 0.01  # Time step in seconds (10ms)
HISTORY_TIME = 0.3  # 0.3 seconds of history
N_STEPS = int(HISTORY_TIME / DT)  # Number of historical steps
PREDICTION_TIME = 350  # Total prediction duration in seconds
PREDICTION_STEPS = int(PREDICTION_TIME / DT)

# Feature columns configuration
TARGET_COLUMNS = ['x', 'y', 'z']
EXCLUDED_COLUMNS = ['delay', 'rocket_id', 'simulation_id']
CATEGORICAL_COLUMNS = ['motor_name', 'fin_cat', 'trigger']


class MLPredictor:
    """
    Machine Learning predictor for rocket trajectories.
    Loads trained model and artifacts, provides prediction functionality.
    """

    def __init__(self):
        """Initialize and load ML model and artifacts"""
        self.model = None
        self.x_scaler = None
        self.y_scaler = None
        self.feature_columns = None
        self.load_artifacts()

    def load_artifacts(self):
        """Load the trained model and preprocessing artifacts"""
        try:
            logger.info("Loading ML model and artifacts...")
            self.model = tf.keras.models.load_model(MODEL_PATH)
            self.x_scaler = joblib.load(X_SCALER_PATH)
            self.y_scaler = joblib.load(Y_SCALER_PATH)
            self.feature_columns = joblib.load(FEATURE_COLUMNS_PATH)
            logger.info("ML model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading ML artifacts: {e}")
            raise RuntimeError(f"Failed to load ML model: {e}")

    def preprocess_input(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Preprocess input DataFrame for model prediction.

        Args:
            df: DataFrame with trajectory history and rocket parameters

        Returns:
            Preprocessed DataFrame ready for scaling
        """
        df = df.copy()

        # Feature Engineering - Calculate velocities
        df['vx'] = df['x'].diff().fillna(0)
        df['vy'] = df['y'].diff().fillna(0)
        df['vz'] = df['z'].diff().fillna(0)

        # Smooth velocities to prevent feedback loops
        for col in ['vx', 'vy', 'vz']:
            df[col] = df[col].rolling(window=3, min_periods=1).mean()

        # Calculate accelerations
        df['ax'] = df['vx'].diff().fillna(0)
        df['ay'] = df['vy'].diff().fillna(0)
        df['az'] = df['vz'].diff().fillna(0)

        # Smooth accelerations
        for col in ['ax', 'ay', 'az']:
            df[col] = df[col].rolling(window=3, min_periods=1).mean()

        # Separate features from targets
        columns_to_drop = TARGET_COLUMNS + EXCLUDED_COLUMNS
        X_df = df.drop(columns=columns_to_drop, axis=1, errors='ignore')

        # Include engineered features
        X_df = pd.concat([X_df, df[['vx', 'vy', 'vz', 'ax', 'ay', 'az']]], axis=1)

        # One-hot encoding for categorical columns
        present_categorical = [col for col in CATEGORICAL_COLUMNS if col in X_df.columns]
        if present_categorical:
            X_df = pd.get_dummies(X_df, columns=present_categorical, drop_first=False)

        # Remove duplicate columns
        X_df = X_df.loc[:, ~X_df.columns.duplicated()]

        # Align columns with training data
        target_features = self.x_scaler.feature_names_in_ if hasattr(self.x_scaler, 'feature_names_in_') else self.feature_columns

        # Add missing columns with zeros
        for col in target_features:
            if col not in X_df.columns:
                X_df[col] = 0

        # Select only relevant columns in correct order
        X_df = X_df[target_features]

        return X_df

    def predict_trajectory(self, user_inputs: Dict, launch_position: List[float] = [0.0, 0.0, 460.0]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Predict rocket trajectory given user inputs.

        Args:
            user_inputs: Dictionary containing all rocket parameters from frontend
            launch_position: Initial [x, y, z] position

        Returns:
            Tuple of (predictions, time_array) where predictions is shape (N, 3)
        """
        logger.info("Starting trajectory prediction...")

        # Create base row with all parameters
        base_row = {
            'x': launch_position[0],
            'y': launch_position[1],
            'z': launch_position[2],
            'delay': 0,
            'rocket_id': 0,
            'simulation_id': 0,
            'time': 0,
            **user_inputs
        }

        # Initialize history buffer (rocket sitting on pad before launch)
        initial_data = []
        for i in range(N_STEPS):
            row = base_row.copy()
            row['time'] = (i - N_STEPS) * DT
            initial_data.append(row)

        history_df = pd.DataFrame(initial_data)

        # Initialize predictions with launch position history
        predictions = [launch_position] * N_STEPS

        # Prepare all prediction sequences
        all_histories = []
        current_time = 0.0
        current_history_df = history_df.copy()

        logger.info(f"Generating {PREDICTION_STEPS} prediction steps...")

        for step in range(PREDICTION_STEPS):
            # Preprocess current history
            X_processed_df = self.preprocess_input(current_history_df)
            X_scaled = self.x_scaler.transform(X_processed_df)

            # Create sequence from last N_STEPS
            if len(X_scaled) < N_STEPS:
                logger.error("History buffer too small")
                break

            current_sequence = X_scaled[-N_STEPS:]
            all_histories.append(current_sequence)

            # Update time
            current_time += DT

            # Create next state for history
            new_row = base_row.copy()
            new_row['time'] = current_time

            # Add temporary placeholder
            new_row_df = pd.DataFrame([new_row])
            current_history_df = pd.concat([current_history_df, new_row_df], ignore_index=True)

            # Keep buffer manageable
            if len(current_history_df) > N_STEPS + 20:
                current_history_df = current_history_df.iloc[-(N_STEPS + 20):]

        # Batch predict all at once
        logger.info(f"Running batch prediction on {len(all_histories)} sequences...")
        all_sequences = np.array(all_histories)
        y_pred_scaled_batch = self.model.predict(all_sequences, verbose=0)
        y_pred_batch = self.y_scaler.inverse_transform(y_pred_scaled_batch)

        # Update predictions
        predictions.extend(y_pred_batch.tolist())

        # Create time array
        time_array = np.arange(len(predictions)) * DT
        predictions_np = np.array(predictions)

        # Calculate statistics
        max_alt = np.max(predictions_np[:, 2])
        final_pos = predictions_np[-1]

        logger.info(f"Prediction complete: Duration={current_time:.2f}s, Max altitude={max_alt:.2f}m, Final position=({final_pos[0]:.1f}, {final_pos[1]:.1f}, {final_pos[2]:.1f})")

        return predictions_np, time_array


# Global predictor instance (singleton)
_predictor_instance: Optional[MLPredictor] = None


def get_predictor() -> MLPredictor:
    """Get or create the global predictor instance"""
    global _predictor_instance
    if _predictor_instance is None:
        _predictor_instance = MLPredictor()
    return _predictor_instance
