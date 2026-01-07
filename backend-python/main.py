"""
FastAPI application for Rocket Simulation API
Provides endpoints for fetching simulations and ML predictions
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any, Optional, Tuple
import logging
import re
import uuid
import time
import numpy as np

# Configure logging FIRST (before any imports that use logger)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from database import (
    SupabaseDatabase,
    RocketNotFoundError,
    DatabaseConnectionError,
    InvalidRocketIDError
)
from parameter_mapper import map_frontend_to_backend

# Import ML predictor and RocketCreator dynamically
try:
    from ml_predictor import get_predictor
    ML_AVAILABLE = True
    logger.info("ML predictor loaded successfully")
except ImportError as e:
    logger.warning(f"ML predictor not available: {e}")
    ML_AVAILABLE = False

try:
    from RocketCreator import RocketCreator
    ROCKETPY_AVAILABLE = True
    logger.info("RocketPy loaded successfully")
except ImportError as e:
    logger.warning(f"RocketPy not available: {e}")
    ROCKETPY_AVAILABLE = False

# Global database instance
db: Optional[SupabaseDatabase] = None


def get_db() -> SupabaseDatabase:
    """Get or create database instance"""
    global db
    if db is None:
        db = SupabaseDatabase()
    return db


# ==================== Application Lifespan ====================

@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Close Rocket API...")
    try:
        get_db()
        logger.info("Database connection established successfully")
    except Exception as e:
        logger.error(f"Failed to connect to database on startup: {e}")

    yield

    # Shutdown
    logger.info("Shutting down Close Rocket API...")


# Initialize FastAPI app with lifespan
app = FastAPI(
    title="Close Rocket API",
    description="API pour récupérer des simulations de trajectoires de fusées et faire des prédictions ML",
    version="2.0.0",
    lifespan=lifespan
)

# CORS configuration for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== Pydantic Models ====================

class RocketParameters(BaseModel):
    """Model for rocket parameters (20 fields)"""
    rocket_id: str
    delay: float
    heading: float
    ramp_inclinaison: float
    motor_name: str
    radius: float
    mass: float
    inertia: str
    center_of_mass_without_motor: float
    cone_length: float
    rocket_length: float
    fin_cat: str
    number_of_ailerons: int
    root_chord: float
    tip_chord: float
    span: float
    fins_pos: float
    fin_inclinaison: float
    drag_coeff: float
    trigger: str
    trajectory_file: str


class TrajectoryPoint(BaseModel):
    """Model for a single trajectory point"""
    time: float
    x: float
    y: float
    z: float
    wind_velocity_x: float
    wind_velocity_y: float


class SimulationData(BaseModel):
    """Model for simulation data (rocket_parameters, trajectory, metadata)"""
    rocket_parameters: RocketParameters
    trajectory: List[TrajectoryPoint]
    metadata: Dict[str, Any]


class SimulationResponse(BaseModel):
    """Model for a complete simulation response - supports single source or both"""
    rocket_id: str
    # For source='rocketpy' or 'ml' - fields at root level
    rocket_parameters: Optional[RocketParameters] = None
    trajectory: Optional[List[TrajectoryPoint]] = None
    metadata: Optional[Dict[str, Any]] = None
    # For source='both' - nested objects
    rocketpy: Optional[SimulationData] = None
    ml: Optional[SimulationData] = None


class SimulationsResponse(BaseModel):
    """Model for multiple simulations response"""
    count: int
    simulations: List[SimulationResponse]


class CoiffeGeometry(BaseModel):
    """Model for nose cone geometry"""
    shape_param: float = Field(..., ge=0, le=1, description="Shape parameter between 0 and 1")
    diameter_mm: float = Field(..., gt=0, description="Diameter in mm")
    length_mm: float = Field(..., gt=0, description="Length in mm")


class TubeGeometry(BaseModel):
    """Model for tube geometry"""
    diameter_mm: float = Field(..., gt=0, description="Diameter in mm")
    length_mm: float = Field(..., gt=0, description="Length in mm")


class AileronGeometry(BaseModel):
    """Model for fin geometry"""
    type: str = Field(..., description="Fin type: trapezoidale, elliptique, or diamant")
    number: int = Field(..., ge=3, description="Number of fins (minimum 3)")
    inclination_deg: float = Field(default=0.0, description="Inclination angle in degrees")

    @field_validator('type')
    @classmethod
    def validate_type(cls, v):
        """Validate fin type is one of allowed values"""
        allowed = ['trapezoidale', 'elliptique', 'diamant']
        if v not in allowed:
            raise ValueError(f'Fin type must be one of {allowed}')
        return v


class Geometry(BaseModel):
    """Model for rocket geometry"""
    coiffe: CoiffeGeometry
    tube: TubeGeometry
    aileron: AileronGeometry


class CenterOfGravity(BaseModel):
    """Model for center of gravity coordinates"""
    x: float
    y: float
    z: float


class Wind(BaseModel):
    """Model for wind conditions"""
    x: float
    y: float
    z: float
    groundSpeed_kms: float = Field(..., description="Ground speed in km/s")


class RampInclination(BaseModel):
    """Model for launch ramp inclination"""
    theta_xy: float = Field(..., description="Theta XY angle in degrees")
    phi_xz: float = Field(..., description="Phi XZ angle in degrees")

    @field_validator('theta_xy', 'phi_xz')
    @classmethod
    def validate_angle(cls, v):
        """Validate angles are reasonable"""
        if not -360 <= v <= 360:
            raise ValueError('Angle must be between -360 and 360 degrees')
        return v


class PredictRequest(BaseModel):
    """Model for ML prediction request from frontend"""
    geometry: Geometry
    cg: CenterOfGravity
    weight_kg: float = Field(..., gt=0, description="Weight in kg")
    thrust_N: float = Field(..., gt=0, description="Thrust in Newtons")
    wind: Wind
    ramp_inclination: RampInclination


class MLPredictionMetrics(BaseModel):
    """Model for ML prediction metrics"""
    max_altitude_m: float
    landing_position: Dict[str, float]  # {"x": float, "y": float}
    flight_duration_s: float
    trajectory_points: int


class ComparisonMetrics(BaseModel):
    """Model for comparison between ML and RocketPy"""
    altitude_difference_m: float
    altitude_difference_percent: float
    horizontal_distance_difference_m: float


class InferenceTimingMetrics(BaseModel):
    """Model for inference timing metrics"""
    ml_ms: float
    simulation_ms: float
    total_ms: float


class PredictResponse(BaseModel):
    """Model for ML prediction response"""
    status: str
    request_id: str
    rocket_id: str
    ml_prediction: MLPredictionMetrics
    rocketpy_simulation: MLPredictionMetrics
    comparison: ComparisonMetrics
    inference_time_ms: InferenceTimingMetrics


# ==================== Helper Functions ====================

def extract_simulation_trajectory(rocket) -> Tuple[np.ndarray, np.ndarray]:
    """
    Extract trajectory data from RocketPy Flight simulation.

    Args:
        rocket: RocketCreator instance with completed flight simulation

    Returns:
        tuple: (trajectory_array, time_array)
            - trajectory_array: np.ndarray shape (N, 3) with [x, y, z] coordinates
            - time_array: np.ndarray shape (N,) with time values in seconds
    """
    flight = rocket.flight
    t_data = flight.time

    def get_col(name, ref_len):
        """Helper to safely extract column data from Flight object"""
        val = getattr(flight, name, None)
        if val is None:
            return np.zeros(ref_len)
        if callable(val):
            return val(t_data)
        elif isinstance(val, np.ndarray):
            return val
        else:
            return np.full(ref_len, val)

    x = get_col('x', len(t_data))
    y = get_col('y', len(t_data))
    z = get_col('z', len(t_data))

    trajectory = np.column_stack([x, y, z])
    return trajectory, t_data


def calculate_metrics(trajectory: np.ndarray, time: np.ndarray) -> Dict[str, Any]:
    """
    Calculate trajectory metrics from position data.

    Args:
        trajectory: np.ndarray shape (N, 3) with [x, y, z] coordinates
        time: np.ndarray shape (N,) with time values

    Returns:
        dict: Metrics including max_altitude_m, landing_position, flight_duration_s, trajectory_points
    """
    return {
        "max_altitude_m": float(np.max(trajectory[:, 2])),
        "landing_position": {
            "x": float(trajectory[-1, 0]),
            "y": float(trajectory[-1, 1])
        },
        "flight_duration_s": float(time[-1]),
        "trajectory_points": len(trajectory)
    }


def calculate_comparison_metrics(ml_metrics: Dict, sim_metrics: Dict) -> Dict[str, float]:
    """
    Calculate comparison metrics between ML and RocketPy simulations.

    Args:
        ml_metrics: Metrics from ML prediction
        sim_metrics: Metrics from RocketPy simulation

    Returns:
        dict: Comparison metrics including altitude differences and horizontal distance
    """
    alt_diff = abs(ml_metrics['max_altitude_m'] - sim_metrics['max_altitude_m'])
    alt_diff_percent = (alt_diff / sim_metrics['max_altitude_m']) * 100 if sim_metrics['max_altitude_m'] > 0 else 0

    ml_landing = ml_metrics['landing_position']
    sim_landing = sim_metrics['landing_position']
    horizontal_distance = np.sqrt(
        (ml_landing['x'] - sim_landing['x'])**2 +
        (ml_landing['y'] - sim_landing['y'])**2
    )

    return {
        "altitude_difference_m": float(alt_diff),
        "altitude_difference_percent": float(alt_diff_percent),
        "horizontal_distance_difference_m": float(horizontal_distance)
    }


# ==================== Exception Handlers ====================

@app.exception_handler(RocketNotFoundError)
async def rocket_not_found_handler(_request, exc):
    """Handle RocketNotFoundError exceptions"""
    logger.warning(f"Rocket not found: {exc}")
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"error": str(exc)}
    )


@app.exception_handler(DatabaseConnectionError)
async def database_error_handler(_request, exc):
    """Handle DatabaseConnectionError exceptions"""
    logger.error(f"Database connection error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Database connection error occurred"}
    )


@app.exception_handler(InvalidRocketIDError)
async def invalid_rocket_id_handler(_request, exc):
    """Handle InvalidRocketIDError exceptions"""
    logger.warning(f"Invalid rocket ID: {exc}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error": str(exc)}
    )


@app.exception_handler(ValueError)
async def validation_error_handler(_request, exc):
    """Handle ValueError exceptions (from Pydantic validators)"""
    logger.warning(f"Validation error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error": str(exc)}
    )


# ==================== API Endpoints ====================

@app.get("/", tags=["Root"])
def read_root():
    """Health check endpoint"""
    return {
        "message": "Close Rocket API v2.0",
        "status": "operational",
        "endpoints": {
            "simulations": "/simulations?ids=rocket_0000,rocket_0001",
            "predict": "/predict (POST)"
        }
    }


@app.get("/simulations", response_model=SimulationsResponse, tags=["Simulations"])
async def get_simulations(
    ids: str = Query(..., description="Comma-separated rocket IDs (e.g., 'rocket_0000,rocket_0001')"),
    source: str = Query("rocketpy", description="Data source: 'rocketpy', 'ml', or 'both'")
):
    """
    Récupère une ou plusieurs simulations complètes par rocket_id

    Args:
        ids: IDs de fusées séparés par virgule (ex: "rocket_0000,rocket_0001")
        source: Source des données - 'rocketpy' (défaut), 'ml', ou 'both'

    Returns:
        JSON complet avec tous les points de trajectoire et paramètres de fusée

    Raises:
        400: Format d'ID invalide ou source invalide
        404: Un ou plusieurs IDs n'existent pas
        500: Erreur de connexion base de données
    """
    # Validate source parameter
    valid_sources = ["rocketpy", "ml", "both"]
    if source not in valid_sources:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid source: '{source}'. Must be one of {valid_sources}"
        )

    logger.info(f"Fetching simulations for IDs: {ids}, source: {source}")

    # Parse comma-separated IDs
    rocket_ids = [rocket_id.strip() for rocket_id in ids.split(',')]

    # Validate format for each ID
    rocket_id_pattern = r'^rocket_\d{4}$'
    for rocket_id in rocket_ids:
        if not re.match(rocket_id_pattern, rocket_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid rocket_id format: '{rocket_id}'. Expected format: rocket_XXXX"
            )

    # Fetch simulations from database based on source
    database = get_db()
    simulations = database.get_simulations_by_ids(rocket_ids, source=source)

    logger.info(f"Successfully fetched {len(simulations)} simulations from {source}")

    return SimulationsResponse(
        count=len(simulations),
        simulations=simulations
    )


@app.post("/predict", response_model=PredictResponse, tags=["Predictions"])
async def predict_trajectory(request: PredictRequest):
    """
    Exécute une prédiction ML et une simulation RocketPy pour la fusée spécifiée.

    Args:
        request: Paramètres complets de la fusée (géométrie, cg, poids, poussée, vent, rampe)

    Returns:
        PredictResponse avec métriques ML, simulation RocketPy et comparaison

    Raises:
        500: Si ML et RocketPy échouent tous les deux
    """
    logger.info(f"Prediction request - Fin: {request.geometry.aileron.type}, Weight: {request.weight_kg}kg, Thrust: {request.thrust_N}N")

    # 1. Generate request_id
    request_id = str(uuid.uuid4())
    total_start = time.time()

    # 2. Map frontend parameters to backend format
    try:
        user_inputs = map_frontend_to_backend(request)
        logger.info(f"Mapped parameters - Motor: {user_inputs['motor_name']}, Heading: {user_inputs['heading']}°")
    except Exception as e:
        logger.error(f"Parameter mapping failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Parameter mapping error: {e}"
        )

    # 3. Get next rocket_id
    database = get_db()
    try:
        rocket_id = database.get_next_rocket_id()
        logger.info(f"Generated rocket_id: {rocket_id}")
    except Exception as e:
        logger.error(f"Failed to generate rocket_id: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate rocket ID"
        )

    # 4. Run ML prediction
    ml_predictions, ml_time, ml_duration_ms = None, None, 0
    ml_error = None
    if ML_AVAILABLE:
        try:
            ml_start = time.time()
            predictor = get_predictor()
            ml_predictions, ml_time = predictor.predict_trajectory(
                user_inputs,
                launch_position=[0.0, 0.0, 460.0]
            )
            ml_duration_ms = (time.time() - ml_start) * 1000
            logger.info(f"ML prediction complete: {len(ml_predictions)} points in {ml_duration_ms:.0f}ms")
        except Exception as e:
            ml_error = str(e)
            logger.error(f"ML prediction failed: {e}")
    else:
        ml_error = "ML predictor not available"
        logger.warning(ml_error)

    # 5. Run RocketPy simulation
    sim_trajectory, sim_time, sim_duration_ms = None, None, 0
    sim_error = None
    if ROCKETPY_AVAILABLE:
        try:
            sim_start = time.time()
            rocket = RocketCreator(**user_inputs)
            sim_trajectory, sim_time = extract_simulation_trajectory(rocket)
            sim_duration_ms = (time.time() - sim_start) * 1000
            logger.info(f"RocketPy simulation complete: {len(sim_trajectory)} points in {sim_duration_ms:.0f}ms")
        except Exception as e:
            sim_error = str(e)
            logger.error(f"RocketPy simulation failed: {e}")
    else:
        sim_error = "RocketPy not available"
        logger.warning(sim_error)

    # 6. Check if both failed
    if ml_error and sim_error:
        logger.error("Both ML and RocketPy failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ML error: {ml_error}. RocketPy error: {sim_error}"
        )

    # 7. Calculate metrics
    ml_metrics = calculate_metrics(ml_predictions, ml_time) if ml_predictions is not None else None
    sim_metrics = calculate_metrics(sim_trajectory, sim_time) if sim_trajectory is not None else None

    # 8. Save to database (non-blocking)
    try:
        if ml_predictions is not None:
            database.save_ml_inference(rocket_id, request_id, user_inputs, ml_predictions, ml_time)
            logger.info(f"Saved ML inference to database")

        if sim_trajectory is not None:
            database.save_rocket_simulation(rocket_id, user_inputs, sim_trajectory, sim_time)
            logger.info(f"Saved RocketPy simulation to database")
    except Exception as e:
        logger.error(f"Database save failed: {e}")
        # Don't block response

    # 9. Calculate comparison (if both available)
    comparison = None
    if ml_metrics and sim_metrics:
        comparison = calculate_comparison_metrics(ml_metrics, sim_metrics)
    else:
        # Fallback comparison if one is missing
        comparison = {
            "altitude_difference_m": 0.0,
            "altitude_difference_percent": 0.0,
            "horizontal_distance_difference_m": 0.0
        }

    total_duration_ms = (time.time() - total_start) * 1000

    # 10. Return response
    return PredictResponse(
        status="success",
        request_id=request_id,
        rocket_id=rocket_id,
        ml_prediction=MLPredictionMetrics(**ml_metrics) if ml_metrics else MLPredictionMetrics(
            max_altitude_m=0, landing_position={"x": 0, "y": 0}, flight_duration_s=0, trajectory_points=0
        ),
        rocketpy_simulation=MLPredictionMetrics(**sim_metrics) if sim_metrics else MLPredictionMetrics(
            max_altitude_m=0, landing_position={"x": 0, "y": 0}, flight_duration_s=0, trajectory_points=0
        ),
        comparison=ComparisonMetrics(**comparison),
        inference_time_ms=InferenceTimingMetrics(
            ml_ms=ml_duration_ms,
            simulation_ms=sim_duration_ms,
            total_ms=total_duration_ms
        )
    )
