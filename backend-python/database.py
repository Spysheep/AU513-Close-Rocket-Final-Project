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
