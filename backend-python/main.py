"""
FastAPI application for Rocket Simulation API
Provides endpoints for fetching simulations and ML predictions
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any, Optional
import logging
import re

from database import (
    SupabaseDatabase,
    RocketNotFoundError,
    DatabaseConnectionError,
    InvalidRocketIDError
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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


class SimulationResponse(BaseModel):
    """Model for a complete simulation response"""
    rocket_id: str
    rocket_parameters: RocketParameters
    trajectory: List[TrajectoryPoint]
    metadata: Dict[str, Any]


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


class PredictResponse(BaseModel):
    """Model for ML prediction response"""
    status: str
    message: str
    request_id: Optional[str] = None


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
async def get_simulations(ids: str = Query(..., description="Comma-separated rocket IDs (e.g., 'rocket_0000,rocket_0001')")):
    """
    Récupère une ou plusieurs simulations complètes par rocket_id

    Args:
        ids: IDs de fusées séparés par virgule (ex: "rocket_0000,rocket_0001")

    Returns:
        JSON complet avec tous les points de trajectoire et paramètres de fusée

    Raises:
        400: Format d'ID invalide
        404: Un ou plusieurs IDs n'existent pas
        500: Erreur de connexion base de données
    """
    logger.info(f"Fetching simulations for IDs: {ids}")

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

    # Fetch simulations from database
    database = get_db()
    simulations = database.get_simulations_by_ids(rocket_ids)

    logger.info(f"Successfully fetched {len(simulations)} simulations")

    return SimulationsResponse(
        count=len(simulations),
        simulations=simulations
    )


@app.post("/predict", response_model=PredictResponse, tags=["Predictions"])
async def predict_trajectory(request: PredictRequest):
    """
    Accepte les paramètres de fusée depuis le frontend pour prédiction ML

    Args:
        request: Paramètres complets de la fusée (géométrie, cg, poids, poussée, vent, rampe)

    Returns:
        Message de succès avec résumé des paramètres

    Note:
        Le modèle ML n'est pas encore implémenté.
        Cet endpoint valide les données et retourne un accusé de réception.

    Future:
        - Appeler service d'inférence ML (modèle deep learning)
        - Retourner trajectoire prédite
        - Fournir scores de confiance et métriques
    """
    logger.info(f"Received prediction request - Fin type: {request.geometry.aileron.type}, Weight: {request.weight_kg} kg, Thrust: {request.thrust_N} N")

    # Log received parameters (for future ML training/analysis)
    logger.debug(f"Prediction parameters: {request.model_dump()}")

    # Calculate thrust-to-weight ratio for validation feedback
    thrust_to_weight = request.thrust_N / (request.weight_kg * 9.81)

    # Build detailed summary message
    summary_message = (
        f"Paramètres de fusée reçus et validés. "
        f"Géométrie: coiffe {request.geometry.coiffe.shape_param} "
        f"({request.geometry.coiffe.diameter_mm}mm × {request.geometry.coiffe.length_mm}mm), "
        f"tube {request.geometry.tube.diameter_mm}mm × {request.geometry.tube.length_mm}mm, "
        f"{request.geometry.aileron.number} ailerons {request.geometry.aileron.type}. "
        f"Masse: {request.weight_kg}kg, Poussée: {request.thrust_N}N (T/W: {thrust_to_weight:.2f}). "
        f"Modèle ML non encore implémenté."
    )

    # Current implementation: validation only
    # Future: Call ML model and return prediction

    return PredictResponse(
        status="success",
        message=summary_message,
        request_id=None
    )
