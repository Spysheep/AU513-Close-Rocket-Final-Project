"""
Database module for Supabase rocket simulations
Manages connection and queries to Supabase PostgreSQL database
"""

import os
import re
import logging
from typing import List, Dict, Optional, Any
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Custom Exceptions
class DatabaseError(Exception):
    """Base exception for database operations"""
    pass


class RocketNotFoundError(DatabaseError):
    """Raised when rocket_id doesn't exist in database"""
    pass


class DatabaseConnectionError(DatabaseError):
    """Raised when Supabase connection fails"""
    pass


class InvalidRocketIDError(DatabaseError):
    """Raised when rocket_id format is invalid"""
    pass


# Singleton pattern for Supabase client
_supabase_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """
    Get or create Supabase client instance (singleton pattern)

    Returns:
        Client: Supabase client instance

    Raises:
        ValueError: If SUPABASE_URL or SUPABASE_KEY are not set
    """
    global _supabase_client
    if _supabase_client is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")

        if not url or not key:
            raise ValueError("SUPABASE_URL et SUPABASE_KEY requis dans le fichier .env")

        _supabase_client = create_client(url, key)
        logger.info("Supabase client initialized successfully")

    return _supabase_client


class SupabaseDatabase:
    """
    Database class for managing rocket simulation data in Supabase

    Handles fetching rocket parameters, trajectory data, and wind conditions
    from Supabase PostgreSQL database.
    """

    def __init__(self):
        """Initialize Supabase database connection"""
        try:
            self.supabase = get_supabase_client()
            logger.info("SupabaseDatabase instance created")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise DatabaseConnectionError(f"Failed to connect to Supabase: {e}")

    def validate_rocket_id_format(self, rocket_id: str) -> bool:
        """
        Validate rocket_id format (must match 'rocket_XXXX' pattern)

        Args:
            rocket_id: The rocket ID to validate

        Returns:
            bool: True if format is valid, False otherwise
        """
        pattern = r'^rocket_\d{4}$'
        return bool(re.match(pattern, rocket_id))

    def rocket_exists(self, rocket_id: str) -> bool:
        """
        Check if rocket_id exists in the database

        Args:
            rocket_id: The rocket ID to check

        Returns:
            bool: True if rocket exists, False otherwise
        """
        try:
            response = self.supabase.table('rockets').select('rocket_id').eq('rocket_id', rocket_id).execute()
            return len(response.data) > 0
        except Exception as e:
            logger.error(f"Error checking rocket existence: {e}")
            raise DatabaseConnectionError(f"Database error: {e}")

    def get_simulation_by_id(self, rocket_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch complete simulation data for a single rocket_id

        Args:
            rocket_id: The rocket ID to fetch

        Returns:
            Dictionary containing:
                - rocket_id: str
                - rocket_parameters: dict with all 20 rocket parameters
                - trajectory: list of trajectory points (time, x, y, z, wind_velocity_x, wind_velocity_y)
                - metadata: dict with calculated statistics

        Raises:
            InvalidRocketIDError: If rocket_id format is invalid
            RocketNotFoundError: If rocket_id doesn't exist
            DatabaseConnectionError: If database query fails
        """
        # Validate format
        if not self.validate_rocket_id_format(rocket_id):
            raise InvalidRocketIDError(f"Invalid rocket_id format: {rocket_id}. Expected format: rocket_XXXX")

        try:
            # Fetch rocket parameters
            logger.info(f"Fetching rocket parameters for {rocket_id}")
            rocket_response = self.supabase.table('rockets').select('*').eq('rocket_id', rocket_id).execute()

            if not rocket_response.data:
                raise RocketNotFoundError(f"Rocket {rocket_id} not found in database")

            rocket_params = rocket_response.data[0]

            # Fetch trajectory data
            logger.info(f"Fetching trajectory data for {rocket_id}")
            trajectory_response = self.supabase.table('trajectories') \
                .select('time, x, y, z') \
                .eq('rocket_id', rocket_id) \
                .order('time') \
                .execute()

            # Fetch wind conditions
            logger.info(f"Fetching wind conditions for {rocket_id}")
            wind_response = self.supabase.table('wind_conditions') \
                .select('time, wind_velocity_x, wind_velocity_y') \
                .eq('rocket_id', rocket_id) \
                .order('time') \
                .execute()

            # Merge trajectory and wind data by time
            trajectory_data = trajectory_response.data
            wind_data = wind_response.data

            # Create a dictionary for quick wind lookup by time
            wind_dict = {point['time']: point for point in wind_data}

            # Combine trajectory and wind data
            combined_trajectory = []
            for traj_point in trajectory_data:
                time = traj_point['time']
                wind_point = wind_dict.get(time, {'wind_velocity_x': 0.0, 'wind_velocity_y': 0.0})

                combined_trajectory.append({
                    'time': time,
                    'x': traj_point['x'],
                    'y': traj_point['y'],
                    'z': traj_point['z'],
                    'wind_velocity_x': wind_point['wind_velocity_x'],
                    'wind_velocity_y': wind_point['wind_velocity_y']
                })

            # Calculate metadata
            metadata = self._calculate_metadata(combined_trajectory)

            # Build complete simulation response
            simulation = {
                'rocket_id': rocket_id,
                'rocket_parameters': {
                    'rocket_id': rocket_params['rocket_id'],
                    'delay': rocket_params['delay'],
                    'heading': rocket_params['heading'],
                    'ramp_inclinaison': rocket_params['ramp_inclinaison'],
                    'motor_name': rocket_params['motor_name'],
                    'radius': rocket_params['radius'],
                    'mass': rocket_params['mass'],
                    'inertia': rocket_params['inertia'],
                    'center_of_mass_without_motor': rocket_params['center_of_mass_without_motor'],
                    'cone_length': rocket_params['cone_length'],
                    'rocket_length': rocket_params['rocket_length'],
                    'fin_cat': rocket_params['fin_cat'],
                    'number_of_ailerons': rocket_params['number_of_ailerons'],
                    'root_chord': rocket_params['root_chord'],
                    'tip_chord': rocket_params['tip_chord'],
                    'span': rocket_params['span'],
                    'fins_pos': rocket_params['fins_pos'],
                    'fin_inclinaison': rocket_params['fin_inclinaison'],
                    'drag_coeff': rocket_params['drag_coeff'],
                    'trigger': rocket_params['trigger'],
                    'trajectory_file': rocket_params['trajectory_file']
                },
                'trajectory': combined_trajectory,
                'metadata': metadata
            }

            logger.info(f"Successfully fetched simulation for {rocket_id}")
            return simulation

        except RocketNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Database error fetching simulation {rocket_id}: {e}")
            raise DatabaseConnectionError(f"Database error: {e}")

    def get_simulations_by_ids(self, rocket_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Fetch multiple simulations by their rocket IDs

        Args:
            rocket_ids: List of rocket IDs to fetch

        Returns:
            List of simulation dictionaries

        Raises:
            InvalidRocketIDError: If any rocket_id format is invalid
            RocketNotFoundError: If any rocket_id doesn't exist
            DatabaseConnectionError: If database query fails
        """
        simulations = []

        for rocket_id in rocket_ids:
            simulation = self.get_simulation_by_id(rocket_id)
            simulations.append(simulation)

        logger.info(f"Successfully fetched {len(simulations)} simulations")
        return simulations

    def _calculate_metadata(self, trajectory: List[Dict[str, float]]) -> Dict[str, Any]:
        """
        Calculate metadata statistics from trajectory data

        Args:
            trajectory: List of trajectory points

        Returns:
            Dictionary with statistics: total_points, duration, max_altitude, landing_position
        """
        if not trajectory:
            return {
                'total_points': 0,
                'duration': 0.0,
                'max_altitude': 0.0,
                'landing_position': {'x': 0.0, 'y': 0.0}
            }

        # Calculate statistics
        max_altitude = max(point['z'] for point in trajectory)
        duration = trajectory[-1]['time'] if trajectory else 0.0
        landing_x = trajectory[-1]['x'] if trajectory else 0.0
        landing_y = trajectory[-1]['y'] if trajectory else 0.0

        return {
            'total_points': len(trajectory),
            'duration': duration,
            'max_altitude': max_altitude,
            'landing_position': {
                'x': landing_x,
                'y': landing_y
            }
        }

    def get_next_rocket_id(self) -> str:
        """
        Get the next available rocket_id by finding the highest existing ID
        and incrementing it.

        Returns:
            str: Next rocket_id in format 'rocket_XXXX' (e.g., 'rocket_1000')

        Raises:
            DatabaseConnectionError: If database query fails
        """
        try:
            # Query to get the highest rocket_id
            result = self.supabase.table('rockets').select('rocket_id').order('rocket_id', desc=True).limit(1).execute()

            if result.data and len(result.data) > 0:
                last_rocket_id = result.data[0]['rocket_id']
                # Extract number from 'rocket_XXXX' format
                match = re.match(r'rocket_(\d+)', last_rocket_id)
                if match:
                    last_number = int(match.group(1))
                    next_number = last_number + 1
                    return f"rocket_{next_number:04d}"
                else:
                    logger.warning(f"Unexpected rocket_id format: {last_rocket_id}, defaulting to rocket_1000")
                    return "rocket_1000"
            else:
                # No rockets in database yet, start from rocket_0000
                logger.info("No rockets found in database, starting from rocket_0000")
                return "rocket_0000"

        except Exception as e:
            logger.error(f"Failed to get next rocket_id: {e}")
            raise DatabaseConnectionError(f"Database query failed: {e}")

    def save_ml_inference(self, rocket_id: str, request_id: str, params: Dict,
                          ml_predictions: Any, ml_time: Any) -> None:
        """
        Save ML inference results to inference tables.

        Saves to:
        - rockets_inference: rocket parameters + request_id
        - trajectories_inference: trajectory points (time, x, y, z)
        - wind_conditions_inference: wind data (time, wind_velocity_x, wind_velocity_y)

        Args:
            rocket_id (str): Unique rocket identifier
            request_id (str): UUID for this inference request
            params (dict): Rocket parameters from map_frontend_to_backend
            ml_predictions (np.ndarray): ML trajectory predictions (N, 3) array [x, y, z]
            ml_time (np.ndarray): Time array (N,) in seconds

        Raises:
            DatabaseConnectionError: If any database operation fails
        """
        try:
            import numpy as np

            # 1. Insert into rockets_inference
            rocket_record = {
                'rocket_id': rocket_id,
                'delay': params.get('delay', 0),
                'heading': params.get('heading'),
                'ramp_inclinaison': params.get('ramp_inclinaison'),
                'motor_name': params.get('motor_name'),
                'radius': params.get('radius'),
                'mass': params.get('mass'),
                'inertia': str(params.get('inertia')),  # Convert tuple to string
                'center_of_mass_without_motor': params.get('center_of_mass_without_motor'),
                'cone_length': params.get('cone_length'),
                'rocket_length': params.get('rocket_length'),
                'fin_cat': params.get('fin_cat'),
                'number_of_ailerons': params.get('number_of_ailerons'),
                'root_chord': params.get('root_chord'),
                'tip_chord': params.get('tip_chord'),
                'span': params.get('span'),
                'fins_pos': params.get('fins_pos'),
                'fin_inclinaison': params.get('fin_inclinaison'),
                'drag_coeff': params.get('drag_coeff'),
                'trigger': params.get('trigger'),
                'trajectory_file': f"{rocket_id}_ml_trajectory.csv"
            }

            self.supabase.table('rockets_inference').insert(rocket_record).execute()
            logger.info(f"Inserted rocket_inference record for {rocket_id}")

            # 2. Batch insert trajectories (chunk by 1000 points)
            trajectory_records = []
            for i, t in enumerate(ml_time):
                trajectory_records.append({
                    'rocket_id': rocket_id,
                    'time': float(t),
                    'x': float(ml_predictions[i, 0]),
                    'y': float(ml_predictions[i, 1]),
                    'z': float(ml_predictions[i, 2])
                })

            # Insert in chunks of 1000
            chunk_size = 1000
            for i in range(0, len(trajectory_records), chunk_size):
                chunk = trajectory_records[i:i+chunk_size]
                self.supabase.table('trajectories_inference').insert(chunk).execute()
                logger.info(f"Inserted trajectory chunk {i//chunk_size + 1} for {rocket_id}")

            # 3. Wind conditions (constant for ML prediction)
            wind_records = []
            wind_x = params.get('wind_velocity_x', 0.0)
            wind_y = params.get('wind_velocity_y', 0.0)

            for t in ml_time:
                wind_records.append({
                    'rocket_id': rocket_id,
                    'time': float(t),
                    'wind_velocity_x': float(wind_x),
                    'wind_velocity_y': float(wind_y)
                })

            # Insert wind conditions in chunks
            for i in range(0, len(wind_records), chunk_size):
                chunk = wind_records[i:i+chunk_size]
                self.supabase.table('wind_conditions_inference').insert(chunk).execute()

            logger.info(f"Successfully saved ML inference for {rocket_id}")

        except Exception as e:
            logger.error(f"Failed to save ML inference: {e}")
            raise DatabaseConnectionError(f"Failed to save ML inference: {e}")

    def save_rocket_simulation(self, rocket_id: str, params: Dict,
                               sim_trajectory: Any, sim_time: Any) -> None:
        """
        Save RocketPy simulation results to standard tables.

        Saves to:
        - rockets: rocket parameters
        - trajectories: trajectory points (time, x, y, z)
        - wind_conditions: wind data (time, wind_velocity_x, wind_velocity_y)

        Args:
            rocket_id (str): Unique rocket identifier (same as ML inference)
            params (dict): Rocket parameters from map_frontend_to_backend
            sim_trajectory (np.ndarray): Simulation trajectory (N, 3) array [x, y, z]
            sim_time (np.ndarray): Time array (N,) in seconds

        Raises:
            DatabaseConnectionError: If any database operation fails
        """
        try:
            import numpy as np

            # 1. Insert into rockets (skip if exists)
            rocket_record = {
                'rocket_id': rocket_id,
                'delay': params.get('delay', 0),
                'heading': params.get('heading'),
                'ramp_inclinaison': params.get('ramp_inclinaison'),
                'motor_name': params.get('motor_name'),
                'radius': params.get('radius'),
                'mass': params.get('mass'),
                'inertia': str(params.get('inertia')),
                'center_of_mass_without_motor': params.get('center_of_mass_without_motor'),
                'cone_length': params.get('cone_length'),
                'rocket_length': params.get('rocket_length'),
                'fin_cat': params.get('fin_cat'),
                'number_of_ailerons': params.get('number_of_ailerons'),
                'root_chord': params.get('root_chord'),
                'tip_chord': params.get('tip_chord'),
                'span': params.get('span'),
                'fins_pos': params.get('fins_pos'),
                'fin_inclinaison': params.get('fin_inclinaison'),
                'drag_coeff': params.get('drag_coeff'),
                'trigger': params.get('trigger'),
                'trajectory_file': f"{rocket_id}_rocketpy_trajectory.csv"
            }

            self.supabase.table('rockets').insert(rocket_record).execute()
            logger.info(f"Inserted rocket record for {rocket_id}")

            # 2. Batch insert trajectories
            trajectory_records = []
            for i, t in enumerate(sim_time):
                trajectory_records.append({
                    'rocket_id': rocket_id,
                    'time': float(t),
                    'x': float(sim_trajectory[i, 0]),
                    'y': float(sim_trajectory[i, 1]),
                    'z': float(sim_trajectory[i, 2])
                })

            # Insert in chunks of 1000
            chunk_size = 1000
            for i in range(0, len(trajectory_records), chunk_size):
                chunk = trajectory_records[i:i+chunk_size]
                self.supabase.table('trajectories').insert(chunk).execute()
                logger.info(f"Inserted trajectory chunk {i//chunk_size + 1} for {rocket_id}")

            # 3. Wind conditions
            wind_records = []
            wind_x = params.get('wind_velocity_x', 0.0)
            wind_y = params.get('wind_velocity_y', 0.0)

            for t in sim_time:
                wind_records.append({
                    'rocket_id': rocket_id,
                    'time': float(t),
                    'wind_velocity_x': float(wind_x),
                    'wind_velocity_y': float(wind_y)
                })

            # Insert wind conditions in chunks
            for i in range(0, len(wind_records), chunk_size):
                chunk = wind_records[i:i+chunk_size]
                self.supabase.table('wind_conditions').insert(chunk).execute()

            logger.info(f"Successfully saved RocketPy simulation for {rocket_id}")

        except Exception as e:
            logger.error(f"Failed to save rocket simulation: {e}")
            raise DatabaseConnectionError(f"Failed to save rocket simulation: {e}")
