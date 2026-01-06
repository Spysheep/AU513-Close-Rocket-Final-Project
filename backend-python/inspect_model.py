import pandas as pd
import joblib
import numpy as np

MODEL_PATH = 'models/trajectory_model.keras'
X_SCALER_PATH = 'models/x_scaler.save'
DATA_FILE = 'dataset_tensorflow.csv'

def inspect():
    print("--- Model Features ---")
    try:
        x_scaler = joblib.load(X_SCALER_PATH)
        if hasattr(x_scaler, 'feature_names_in_'):
            print(f"Features expected by Scaler ({len(x_scaler.feature_names_in_)}):")
            for f in x_scaler.feature_names_in_:
                print(f" - {f}")
        else:
            print("Scaler does not have feature_names_in_.")
    except Exception as e:
        print(f"Error loading scaler: {e}")

    print("\n--- Dataset values ---")
    try:
        df = pd.read_csv(DATA_FILE)
        print("Unique Motor Names:", df['motor_name'].unique())
        print("Unique Fin Cats:", df['fin_cat'].unique())
        print("Unique Triggers:", df['trigger'].unique())
        print(f"Unique Rocket IDs: {len(df['rocket_id'].unique())} (Showing first 5)")
        print(df['rocket_id'].unique()[:5])
        
        # Check if geometry columns are constant per rocket_id
        cols_to_check = ['mass', 'radius', 'rocket_length']
        for col in cols_to_check:
            print(f"{col} mean:", df[col].mean())
            
    except Exception as e:
        print(f"Error loading dataset: {e}")

if __name__ == "__main__":
    inspect()
