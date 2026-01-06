import joblib
import pandas as pd
import numpy as np

def inspect_artifacts():
    try:
        x_scaler = joblib.load('models/x_scaler.save')
        feature_columns = joblib.load('models/feature_columns.save')
        
        print("--- Feature Columns (joblib) ---")
        print(feature_columns)
        
        print("\n--- Scalar Feature Names (if available) ---")
        if hasattr(x_scaler, 'feature_names_in_'):
            print(list(x_scaler.feature_names_in_))
        else:
            print("Scaler does not have feature_names_in_")
            
        print("\n--- Scalar Mean ---")
        print(x_scaler.mean_)
        
        print("\n--- Scalar Scale ---")
        print(x_scaler.scale_)

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_artifacts()
