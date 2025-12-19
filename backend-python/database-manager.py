"""
Database Manager for Rocket Data on Supabase
Manages rocket parameters and trajectory data storage
"""

import os
import csv
import glob
from pathlib import Path
from supabase import create_client, Client
from dotenv import load_dotenv
from typing import List, Dict, Any

# Load environment variables
load_dotenv()

class SupabaseRocketDB:
    def __init__(self):
        """Initialize Supabase client with credentials from .env file"""
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")

        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env file")

        self.supabase: Client = create_client(url, key)
        self.dataset_path = Path(__file__).parent / "DatasetGenerator" / "dataset"

    def create_tables(self):
        """
        Create necessary tables in Supabase database.
        Note: Execute these SQL commands in Supabase SQL Editor
        """
        sql_commands = """
        -- Table for rocket input parameters
        CREATE TABLE IF NOT EXISTS rockets (
            rocket_id TEXT PRIMARY KEY,
            delay FLOAT,
            heading FLOAT,
            ramp_inclinaison FLOAT,
            motor_name TEXT,
            radius FLOAT,
            mass FLOAT,
            inertia TEXT,
            center_of_mass_without_motor FLOAT,
            cone_length FLOAT,
            rocket_length FLOAT,
            fin_cat TEXT,
            number_of_ailerons INT,
            root_chord FLOAT,
            tip_chord FLOAT,
            span FLOAT,
            fins_pos FLOAT,
            fin_inclinaison FLOAT,
            drag_coeff FLOAT,
            trigger TEXT,
            trajectory_file TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
        );

        -- Table for wind conditions
        CREATE TABLE IF NOT EXISTS wind_conditions (
            id BIGSERIAL PRIMARY KEY,
            rocket_id TEXT REFERENCES rockets(rocket_id) ON DELETE CASCADE,
            time FLOAT,
            wind_velocity_x FLOAT,
            wind_velocity_y FLOAT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
        );

        -- Table for trajectory data points
        CREATE TABLE IF NOT EXISTS trajectories (
            id BIGSERIAL PRIMARY KEY,
            rocket_id TEXT REFERENCES rockets(rocket_id) ON DELETE CASCADE,
            time FLOAT,
            x FLOAT,
            y FLOAT,
            z FLOAT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
        );

        -- Create indexes for faster queries
        CREATE INDEX IF NOT EXISTS idx_wind_conditions_rocket_id ON wind_conditions(rocket_id);
        CREATE INDEX IF NOT EXISTS idx_wind_conditions_time ON wind_conditions(rocket_id, time);
        CREATE INDEX IF NOT EXISTS idx_trajectories_rocket_id ON trajectories(rocket_id);
        CREATE INDEX IF NOT EXISTS idx_trajectories_time ON trajectories(rocket_id, time);
        """

        print("SQL commands to create tables:")
        print("=" * 80)
        print(sql_commands)
        print("=" * 80)
        print("\nPlease execute these commands in Supabase SQL Editor:")
        print("https://supabase.com/dashboard/project/_/sql")

        return sql_commands

    def load_master_rocket_inputs(self) -> List[Dict[str, Any]]:
        """Load rocket parameters from master_rocket_inputs.csv"""
        master_file = self.dataset_path / "master_rocket_inputs.csv"

        if not master_file.exists():
            raise FileNotFoundError(f"Master file not found: {master_file}")

        rockets = []
        with open(master_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rocket_data = {
                    'rocket_id': row['rocket_id'],
                    'delay': float(row['delay']),
                    'heading': float(row['heading']),
                    'ramp_inclinaison': float(row['ramp_inclinaison']),
                    'motor_name': row['motor_name'],
                    'radius': float(row['radius']),
                    'mass': float(row['mass']),
                    'inertia': row['inertia'],
                    'center_of_mass_without_motor': float(row['center_of_mass_without_motor']),
                    'cone_length': float(row['cone_length']),
                    'rocket_length': float(row['rocket_length']),
                    'fin_cat': row['fin_cat'],
                    'number_of_ailerons': int(row['number_of_ailerons']),
                    'root_chord': float(row['root_chord']),
                    'tip_chord': float(row['tip_chord']),
                    'span': float(row['span']),
                    'fins_pos': float(row['fins_pos']),
                    'fin_inclinaison': float(row['fin_inclinaison']),
                    'drag_coeff': float(row['drag_coeff']),
                    'trigger': row['trigger'],
                    'trajectory_file': row['trajectory_file']
                }
                rockets.append(rocket_data)

        print(f"Loaded {len(rockets)} rocket configurations")
        return rockets

    def insert_rockets(self, rockets: List[Dict[str, Any]]) -> None:
        """Insert rocket data into Supabase rockets table"""
        try:
            response = self.supabase.table('rockets').insert(rockets).execute()
            print(f"Successfully inserted {len(rockets)} rockets into database")
            return response
        except Exception as e:
            print(f"Error inserting rockets: {e}")
            raise

    def load_trajectory_file(self, trajectory_file: str, rocket_id: str) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Load trajectory and wind data from a single CSV file

        Returns:
            tuple: (trajectory_points, wind_points)
        """
        # Construct full path
        trajectory_path = self.dataset_path / trajectory_file

        if not trajectory_path.exists():
            print(f"Warning: Trajectory file not found: {trajectory_path}")
            return [], []

        trajectory_points = []
        wind_points = []

        with open(trajectory_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Trajectory data (position only)
                trajectory_point = {
                    'rocket_id': rocket_id,
                    'time': float(row['time']),
                    'x': float(row['x']),
                    'y': float(row['y']),
                    'z': float(row['z'])
                }
                trajectory_points.append(trajectory_point)

                # Wind data (separate table)
                wind_point = {
                    'rocket_id': rocket_id,
                    'time': float(row['time']),
                    'wind_velocity_x': float(row['wind_velocity_x']),
                    'wind_velocity_y': float(row['wind_velocity_y'])
                }
                wind_points.append(wind_point)

        return trajectory_points, wind_points

    def insert_trajectories_batch(self, trajectory_points: List[Dict[str, Any]], batch_size: int = 1000) -> None:
        """Insert trajectory data in batches to avoid size limits"""
        total_points = len(trajectory_points)

        for i in range(0, total_points, batch_size):
            batch = trajectory_points[i:i + batch_size]
            try:
                self.supabase.table('trajectories').insert(batch).execute()
                print(f"  Inserted trajectory batch {i//batch_size + 1}: {len(batch)} points")
            except Exception as e:
                print(f"  Error inserting trajectory batch {i//batch_size + 1}: {e}")
                raise

    def insert_wind_conditions_batch(self, wind_points: List[Dict[str, Any]], batch_size: int = 1000) -> None:
        """Insert wind conditions data in batches to avoid size limits"""
        total_points = len(wind_points)

        for i in range(0, total_points, batch_size):
            batch = wind_points[i:i + batch_size]
            try:
                self.supabase.table('wind_conditions').insert(batch).execute()
                print(f"  Inserted wind batch {i//batch_size + 1}: {len(batch)} points")
            except Exception as e:
                print(f"  Error inserting wind batch {i//batch_size + 1}: {e}")
                raise

    def import_all_data(self):
        """Import all rocket, trajectory, and wind data into Supabase"""
        print("\n" + "=" * 80)
        print("STARTING DATA IMPORT TO SUPABASE")
        print("=" * 80 + "\n")

        # Step 1: Load and insert rocket data
        print("Step 1: Loading master rocket inputs...")
        rockets = self.load_master_rocket_inputs()

        print("Step 2: Inserting rockets into database...")
        self.insert_rockets(rockets)

        # Step 2: Load and insert trajectory and wind data
        print("\nStep 3: Loading and inserting trajectory and wind data...")
        trajectory_files = sorted(glob.glob(str(self.dataset_path / "trajectories" / "*.csv")))

        total_files = len(trajectory_files)
        for idx, traj_file in enumerate(trajectory_files, 1):
            # Extract rocket_id from filename (e.g., rocket_0000_trajectory.csv -> rocket_0000)
            filename = Path(traj_file).stem
            rocket_id = filename.replace('_trajectory', '')

            print(f"\n[{idx}/{total_files}] Processing {rocket_id}...")

            # Load trajectory and wind data
            trajectory_points, wind_points = self.load_trajectory_file(
                f"trajectories\\{Path(traj_file).name}",
                rocket_id
            )

            if trajectory_points and wind_points:
                print(f"  Loaded {len(trajectory_points)} trajectory points and {len(wind_points)} wind points")
                self.insert_trajectories_batch(trajectory_points)
                self.insert_wind_conditions_batch(wind_points)
            else:
                print(f"  No data found")

        print("\n" + "=" * 80)
        print("DATA IMPORT COMPLETED SUCCESSFULLY")
        print("=" * 80)

    def clear_all_data(self):
        """Clear all data from tables (use with caution!)"""
        confirmation = input("Are you sure you want to delete ALL data? (yes/no): ")
        if confirmation.lower() == 'yes':
            try:
                self.supabase.table('wind_conditions').delete().neq('id', 0).execute()
                print("Cleared wind_conditions table")

                self.supabase.table('trajectories').delete().neq('id', 0).execute()
                print("Cleared trajectories table")

                self.supabase.table('rockets').delete().neq('rocket_id', '').execute()
                print("Cleared rockets table")
            except Exception as e:
                print(f"Error clearing data: {e}")
        else:
            print("Operation cancelled")

    def get_rocket_stats(self):
        """Get statistics about stored data"""
        try:
            rockets_count = self.supabase.table('rockets').select('rocket_id', count='exact').execute()
            trajectories_count = self.supabase.table('trajectories').select('id', count='exact').execute()
            wind_count = self.supabase.table('wind_conditions').select('id', count='exact').execute()

            print("\nDatabase Statistics:")
            print(f"  Total rockets: {rockets_count.count}")
            print(f"  Total trajectory points: {trajectories_count.count}")
            print(f"  Total wind condition points: {wind_count.count}")
        except Exception as e:
            print(f"Error getting stats: {e}")


def main():
    """Main function to demonstrate usage"""
    print("Supabase Rocket Database Manager")
    print("=" * 80)

    # Initialize database manager
    db = SupabaseRocketDB()

    # Display menu
    print("\nAvailable operations:")
    print("1. Show SQL commands to create tables")
    print("2. Import all data (rockets + trajectories)")
    print("3. Clear all data")
    print("4. Show database statistics")
    print("5. Exit")

    while True:
        choice = input("\nEnter your choice (1-5): ").strip()

        if choice == '1':
            db.create_tables()
        elif choice == '2':
            db.import_all_data()
        elif choice == '3':
            db.clear_all_data()
        elif choice == '4':
            db.get_rocket_stats()
        elif choice == '5':
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please enter 1-5.")


if __name__ == "__main__":
    main()
