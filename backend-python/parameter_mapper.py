"""
Parameter mapping module for Close Rocket API
Maps frontend parameters to backend RocketCreator/ML model format
"""

from typing import Dict, Tuple
from pydantic import BaseModel


def select_motor_from_thrust(thrust_N: float) -> str:
    """
    Select appropriate motor based on thrust requirement.

    Args:
        thrust_N (float): Required thrust in Newtons

    Returns:
        str: Motor name compatible with RocketCreator
    """
    if thrust_N < 30:
        return "Pro24-6G"
    elif thrust_N < 80:
        return "Pro54-5G Barasinga"
    elif thrust_N < 150:
        return "Pro75-3G"
    else:
        return "Pro75M1670"


def calculate_derived_parameters(geometry, mass: float) -> Dict[str, any]:
    """
    Calculate derived rocket parameters from geometry and mass.

    Calculates:
    - Inertia tensor based on cylindrical geometry
    - Default fin dimensions if not provided

    Args:
        geometry: Geometry object from PredictRequest (coiffe, tube, aileron)
        mass (float): Total rocket mass in kg

    Returns:
        dict: Dictionary with 'inertia', 'root_chord', 'tip_chord', 'span'
    """
    # Convert mm to m
    radius = geometry.tube.diameter_mm / 2000  # mm → m
    length = geometry.tube.length_mm / 1000  # mm → m

    # Calculate moments of inertia for a cylinder
    # Ix = Iy = (1/12) * m * L² + (1/4) * m * R²  (perpendicular to axis)
    # Iz = (1/2) * m * R²  (along axis)
    Ix = Iy = (1/12) * mass * length**2 + (1/4) * mass * radius**2
    Iz = (1/2) * mass * radius**2

    inertia = (Ix, Iy, Iz)

    # Default fin dimensions based on rocket size
    # Root chord ~15% of rocket length, tip chord ~8%, span ~17%
    root_chord = length * 0.15
    tip_chord = length * 0.08
    span = radius * 1.7

    return {
        'inertia': inertia,
        'root_chord': root_chord,
        'tip_chord': tip_chord,
        'span': span
    }


def map_frontend_to_backend(request) -> Dict[str, any]:
    """
    Map frontend PredictRequest parameters to backend RocketCreator format.

    Performs:
    - Unit conversions (mm → m)
    - Type mapping ('trapezoidale' → 'trapezoidal')
    - Motor selection from thrust
    - Derived parameter calculation

    Args:
        request: PredictRequest object from FastAPI

    Returns:
        dict: Parameters compatible with RocketCreator and ML model
    """
    # Map fin type (French → English)
    fin_type_mapping = {
        'trapezoidale': 'trapezoidal',
        'elliptique': 'elyptique',  # Note: RocketCreator uses 'elyptique' (typo in original)
        'diamant': 'trapezoidal'  # Fallback to trapezoidal for diamond shape
    }

    fin_cat = fin_type_mapping.get(
        request.geometry.aileron.type.lower(),
        'trapezoidal'  # Default fallback
    )

    # Use motor_name directly from request (user selects it in frontend)
    # No longer derive it from thrust_N
    motor_name = request.motor_name

    # Calculate derived parameters
    derived = calculate_derived_parameters(request.geometry, request.weight_kg)

    # Build complete parameter dict
    user_inputs = {
        # Motor and trigger
        'motor_name': motor_name,
        'trigger': 'apogee',
        'delay': 0,

        # Orientation and launch
        'heading': request.ramp_inclination.phi_xz,
        'ramp_inclinaison': request.ramp_inclination.theta_xy,

        # Wind conditions
        'wind_velocity_x': request.wind.x,
        'wind_velocity_y': request.wind.y,

        # Rocket geometry (convert mm → m)
        'radius': request.geometry.tube.diameter_mm / 2000,
        'cone_length': request.geometry.coiffe.length_mm / 1000,
        'rocket_length': request.geometry.tube.length_mm / 1000,

        # Mass and center of gravity
        'mass': request.weight_kg,
        'center_of_mass_without_motor': request.cg.x,

        # Inertia (derived)
        'inertia': derived['inertia'],

        # Fin configuration
        'fin_cat': fin_cat,
        'number_of_ailerons': request.geometry.aileron.number,
        'fin_inclinaison': request.geometry.aileron.inclination_deg,
        'fins_pos': 0.04,  # Default position

        # Fin dimensions (derived)
        'root_chord': derived['root_chord'],
        'tip_chord': derived['tip_chord'],
        'span': derived['span'],

        # Parachute
        'drag_coeff': 1.0,  # Default drag coefficient
    }

    return user_inputs
