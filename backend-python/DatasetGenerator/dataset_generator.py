import numpy as np
import pandas as pd
import random
import os
import datetime
import traceback
# Import the tqdm library
from tqdm import tqdm
from RocketCreator import RocketCreator

# --- Configuration ---
NUM_ROCKETS_TO_GENERATE = 5
OUTPUT_DIR = "dataset"
TRAJECTORY_DIR = os.path.join(OUTPUT_DIR, "trajectories")
WIND_DIR = os.path.join(OUTPUT_DIR, "wind")
KLM_DIR = os.path.join(OUTPUT_DIR, "klm_files")
MASTER_INPUT_FILE = os.path.join(OUTPUT_DIR, "master_rocket_inputs.csv")

# Ensure output directories exist
os.makedirs(TRAJECTORY_DIR, exist_ok=True)
os.makedirs(WIND_DIR, exist_ok=True)  # Added for completeness
os.makedirs(KLM_DIR, exist_ok=True)  # Added for completeness

# Define choices for categorical parameters
MOTOR_CHOICES = ["Pro75M1670", "Pro75-3G", "Pro54-5G Barasinga"]
FIN_CHOICES = ["trapezoidal", "elyptique"]
TRIGGER_CHOICES = ["apogee"]  # You can add numerical values, e.g., "apogee", 10, 15


def get_random_params():
    """
    Generates a dictionary of randomized parameters for a single rocket.

    ************************************************************************
    *** CRITICAL: You MUST adjust these ranges to be physically realistic ***
    *** for your use case. Bad ranges will cause simulations to fail.    ***
    ************************************************************************
    """

    # Rocket body
    radius = random.uniform(0.04, 0.30)  # 4cm to 10cm radius
    rocket_length = random.uniform(1.5, 3.0)  # 1.5m to 3.0m length
    cone_length = random.uniform(0.1, 0.5)  # 30cm to 70cm

    # Mass and Inertia
    mass = random.uniform(5, 30.0)  # 10kg to 30kg
    center_of_mass_without_motor = random.uniform(0.8, rocket_length * 0.7)
    # Inertia: (Ix, Iy, Iz). Ix and Iy are similar, Iz (roll) is small.
    inertia_ixy = random.uniform(mass * 0.5, mass * 1.5)
    inertia_iz = random.uniform(mass * 0.001, mass * 0.005)
    inertia = (inertia_ixy, inertia_ixy, inertia_iz)

    # Fins
    number_of_ailerons = random.randint(3, 8)
    root_chord = random.uniform(0.30, 0.70)  # 10cm to 25cm
    tip_chord = random.uniform(0, root_chord * 0.8)  # Tip must be <= root
    span = random.uniform(0.15, 0.5)  # 8cm to 20cm
    fins_pos = random.uniform(0.0, 0.2)  # Position from base
    fin_inclinaison = random.uniform(0.0, 1.0)  # 0 to 1 degrees

    # Flight parameters
    delay = random.randint(0, 10)  # Days from today
    heading = random.uniform(0, 360)  # 0-360 degrees
    ramp_inclinaison = random.uniform(80, 89)  # 80-89 degrees

    # Parachute
    drag_coeff = random.uniform(0.8, 1.5)

    params = {
        "delay": delay,
        "heading": heading,
        "ramp_inclinaison": ramp_inclinaison,
        "motor_name": random.choice(MOTOR_CHOICES),
        "radius": radius,
        "mass": mass,
        "inertia": inertia,
        "center_of_mass_without_motor": center_of_mass_without_motor,
        "cone_length": cone_length,
        "rocket_length": rocket_length,
        "fin_cat": random.choice(FIN_CHOICES),
        "number_of_ailerons": number_of_ailerons,
        "root_chord": root_chord,
        "tip_chord": tip_chord,
        "span": span,
        "fins_pos": fins_pos,
        "fin_inclinaison": fin_inclinaison,
        "drag_coeff": drag_coeff,
        "trigger": random.choice(TRIGGER_CHOICES),
    }
    return params

# ... (Imports and get_random_params remain the same) ...
# Define ANSI color code for Cobalt Blue (Bright Blue)
COBALT_BLUE = '\033[94m'
RESET_COLOR = '\033[94m'


def main():
    print(f"Starting dataset generation. Target: {NUM_ROCKETS_TO_GENERATE} stable rockets.")

    successful_simulations = []
    rocket_id_counter = 0
    success_count = 0
    failure_count = 0

    # Initialize tqdm with the target number of successful rockets.
    # The bar_format is heavily customized to:
    # 1. Apply COBALT_BLUE to the entire description, percentage, counts, and bar itself.
    # 2. Remove time/rate info.
    pbar = tqdm(
        total=NUM_ROCKETS_TO_GENERATE,
        desc=f"{COBALT_BLUE}Generating Dataset{RESET_COLOR}",
        unit=" rocket",
        # Apply color codes to the elements we want colored
        bar_format=f'{COBALT_BLUE}{{desc}}: {{percentage:3.0f}}%|{{bar}}| {{n_fmt}}/{{total_fmt}}, {{postfix}}{RESET_COLOR}'
    )

    while success_count < NUM_ROCKETS_TO_GENERATE:

        try:
            # 1. Generate random inputs
            params = get_random_params()

            # 2. Create the rocket instance
            rocket_sim = RocketCreator(**params)
            rocket_id_counter += 1  # Increment attempt counter here

            # 3. Check for stability
            if not rocket_sim.is_stable():
                failure_count += 1

                # --- Progress Bar Update (Failure) ---
                # Status is now 'Unstable'
                pbar.set_postfix({
                    'status': 'Unstable',
                    'success': success_count,  # Simplified to count only
                    'failure': failure_count  # Simplified to count only
                })
                continue

            # 4. Save the data (Success path)
            rocket_id = f"rocket_{len(successful_simulations):04d}"
            wind_filename = f"{rocket_id}_wind.csv"
            wind_filepath = os.path.join(WIND_DIR, wind_filename)
            klm_filename = f"{rocket_id}_klm.kml"
            kml_filepath = os.path.join(KLM_DIR, klm_filename)
            trajectory_filename = f"{rocket_id}_trajectory.csv"
            trajectory_filepath = os.path.join(TRAJECTORY_DIR, trajectory_filename)

            # Call the plot_flight method
            rocket_sim.plot_flight(
                trajectory_filepath=trajectory_filepath,
                show_plots=False,
                wind_filepath=wind_filepath,
                kml_filepath=kml_filepath
            )

            # 5. Store input parameters
            input_data = params.copy()
            input_data['rocket_id'] = rocket_id
            input_data['trajectory_file'] = trajectory_filepath
            input_data['inertia'] = str(input_data['inertia'])

            successful_simulations.append(input_data)
            success_count += 1

            # --- Progress Bar Update (Success) ---
            pbar.update(1)  # Only update the bar on successful generation
            # Status is now 'Stable'
            pbar.set_postfix({
                'status': 'Stable',
                'success': success_count,  # Simplified to count only
                'failure': failure_count  # Simplified to count only
            })
            # -------------------------------------

        except Exception as e:
            failure_count += 1

            # --- Progress Bar Update (Error/Failure) ---
            # Status is now 'Unstable' (due to error)
            pbar.set_postfix({
                'status': 'Unstable',
                'success': success_count,  # Simplified to count only
                'failure': failure_count  # Simplified to count only
            })
            # -------------------------------------------

    # Close the progress bar when the loop is complete
    pbar.close()

    # 6. Save the master input file
    master_input_df = pd.DataFrame(successful_simulations)
    master_input_df.to_csv(MASTER_INPUT_FILE, index=False)

    print("\n--- Generation Complete ---")
    print(f"Successfully generated {len(successful_simulations)} rocket simulations.")
    print(f"Total attempts made (including failures): {rocket_id_counter}")
    print(f"Master input data saved to: {MASTER_INPUT_FILE}")


if __name__ == "__main__":
    main()