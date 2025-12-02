import pandas as pd
import os
from tqdm import tqdm  # Optional: for a progress bar

# 1. Setup paths
BASE_DIR = 'C:/Users/arthu/PycharmProjects/ClosedRocket/dataset'  # Root folder of your data
BASE_DIR_TRAJECTORY = 'C:/Users/arthu/PycharmProjects/ClosedRocket'
INPUT_FILE = os.path.join(BASE_DIR, 'master_rocket_inputs_with_init_wind.csv')

# 2. Load the Master Input File
df_inputs = pd.read_csv(INPUT_FILE)

# Display the first few rows to ensure it loaded
print(f"Loaded {len(df_inputs)} input configurations.")

# 3. Create a list to hold all the merged dataframes
all_simulations = []

# 4. Iterate through the input file
# Replace 'trajectory_file_column' with the actual name of the column in your CSV
path_col = 'trajectory_file'

for index, row in tqdm(df_inputs.iterrows(), total=df_inputs.shape[0]):

    # A. Construct the full path to the trajectory file
    # If the CSV contains 'trajectories/rocket_0001.csv', this works:
    traj_path = os.path.join(BASE_DIR_TRAJECTORY, row[path_col])

    # B. Load the specific trajectory
    if os.path.exists(traj_path):
        df_traj = pd.read_csv(traj_path)

        # C. Propagate Input Data (The Merge Step)
        # We take the static inputs from 'row' and assign them to new columns
        # in the trajectory dataframe. This repeats the static values for every time step.
        for col_name in df_inputs.columns:
            if col_name != path_col:  # Don't need the file path in the training data
                df_traj[col_name] = row[col_name]

        # D. Add an ID (Optional but recommended)
        # Useful to know which simulation a row belongs to later
        df_traj['simulation_id'] = index

        all_simulations.append(df_traj)
    else:
        print(f"Warning: File not found at {traj_path}")

# 5. Concatenate into one massive dataset
final_dataset = pd.concat(all_simulations, ignore_index=True)

print(f"Final dataset shape: {final_dataset.shape}")
print(final_dataset.head())

final_dataset.to_csv('dataset_tensorflow.csv', index=False)