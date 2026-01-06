import pandas as pd

def check_feature_variance():
    try:
        df = pd.read_csv('dataset_tensorflow.csv')
        
        # Group by simulation to see if mass changes within a flight
        if 'simulation_id' in df.columns:
            sim_ids = df['simulation_id'].unique()
            target_sim = df[df['simulation_id'] == sim_ids[0]]
            
            print(f"--- Simulation {sim_ids[0]} ---")
            features_to_check = ['mass', 'center_of_mass_without_motor', 'ix', 'iy', 'iz', 'heading', 'ramp_inclinaison']
            
            for f in features_to_check:
                if f in target_sim.columns:
                    unique_vals = target_sim[f].nunique()
                    min_val = target_sim[f].min()
                    max_val = target_sim[f].max()
                    print(f"Feature '{f}': {unique_vals} unique values. Range: [{min_val}, {max_val}]")
                    if unique_vals > 1:
                        print(f"  -> Dynamic!")
                    else:
                        print(f"  -> Static.")
        else:
            print("No simulation_id column.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_feature_variance()
