import numpy as np
import pandas as pd
import os
from rocketpy import Environment, Rocket, Flight
from rocketpy.simulation import FlightDataExporter
import motor_closed_rocket as mc
import datetime


class RocketCreator:
    def __init__(self, delay=0, heading=220, ramp_inclinaison=85, motor_name="Pro75M1670",
                 radius=127 / 2000, mass=14.426, inertia=(6.321, 6.321, 0.034),
                 center_of_mass_without_motor=1, cone_length=0.558, rocket_length=2.53,
                 fin_cat="trapezoidal", number_of_ailerons=4, root_chord=0.120,
                 tip_chord=0.060, span=0.110, fins_pos=0, fin_inclinaison=0.0,
                 drag_coeff=1.0, trigger="apogee", wind_velocity_x=None, wind_velocity_y=None):

        # Constants
        self.EARTH_RADIUS = 6371000
        self.latitude_0 = 43.218436
        self.longitude_0 = 0.047333
        self.altitude_0 = 409
        self.r = self.EARTH_RADIUS + self.altitude_0

        # Ramp & Motor info
        self.heading = heading
        self.ramp_inclinaison = ramp_inclinaison
        
        # Wind parameters
        self.wind_velocity_x = wind_velocity_x
        self.wind_velocity_y = wind_velocity_y
        self.motor_name = motor_name

        # Rocket data
        self.radius = radius
        self.mass = mass
        self.inertia = inertia
        self.center_of_mass_without_motor = center_of_mass_without_motor
        self.cone_length = cone_length
        self.rocket_length = rocket_length
        self.number_of_fins = number_of_ailerons
        self.root_chord = root_chord
        self.tip_chord = tip_chord
        self.span = span
        self.fins_pos = fins_pos
        self.fin_inclinaison = fin_inclinaison
        self.drag_coeff = drag_coeff
        self.trigger = trigger

        # Environment
        self.environment = Environment(latitude=self.latitude_0, longitude=self.longitude_0, elevation=self.altitude_0)
        self.date = datetime.date.today() + datetime.timedelta(days=delay)
        self.environment.set_date((self.date.year, self.date.month, self.date.day, 12))

        # Robust Atmosphere Loading
        try:
            self.environment.set_atmospheric_model(type="forecast", file="GFS")
        except Exception:
            print("Warning: GFS forecast failed/offline. Using Standard Atmosphere.")
            self.environment.set_atmospheric_model(type="standard_atmosphere")

        # Motor
        motor_loader = mc.MotorClosedRocket()
        self.motor = motor_loader.get_motor(motor_name)

        # Drag Files Check (Prevents crash if files missing)
        drag_off = "data/rocket/calisto/powerOffDragCurve.csv"
        drag_on = "data/rocket/calisto/powerOnDragCurve.csv"

        # Use constant drag if files are missing
        if os.path.exists(drag_off) and os.path.exists(drag_on):
            p_off, p_on = drag_off, drag_on
        else:
            p_off, p_on = 0.5, 0.6  # Default fallbacks

        # Rocket Setup
        self.rocket = Rocket(
            radius=self.radius,
            mass=self.mass,
            inertia=self.inertia,
            power_off_drag=p_off,
            power_on_drag=p_on,
            center_of_mass_without_motor=self.center_of_mass_without_motor,
            coordinate_system_orientation="tail_to_nose",
        )
        self.rocket.add_motor(self.motor, position=0)

        # Nose Cone
        self.nose_cone = self.rocket.add_nose(
            length=self.cone_length, kind="von karman", position=self.rocket_length
        )

        # Fins
        fin_position = self.fins_pos + self.root_chord  # Adjust for tail-to-nose
        if fin_cat == "trapezoidal":
            self.fin_set = self.rocket.add_trapezoidal_fins(
                n=self.number_of_fins,
                root_chord=self.root_chord,
                tip_chord=self.tip_chord,
                span=self.span,
                position=fin_position,
                cant_angle=self.fin_inclinaison,
            )
        elif fin_cat == "elyptique":
            self.fin_set = self.rocket.add_elliptical_fins(
                n=self.number_of_fins,
                root_chord=self.root_chord,
                span=self.span,
                position=fin_position,
                cant_angle=self.fin_inclinaison,
            )

        # Tail & Parachute
        self.tail = self.rocket.add_tail(
            top_radius=self.radius, bottom_radius=self.radius - 0.02, length=0.05, position=0
        )
        self.para = self.rocket.add_parachute(
            name="para",
            cd_s=self.drag_coeff,
            trigger=self.trigger,
        )

        # Flight
        self.flight = Flight(rocket=self.rocket, environment=self.environment, rail_length=5.2,
                             inclination=self.ramp_inclinaison, heading=self.heading)
        
        # Apply constant wind if provided
        if self.wind_velocity_x is not None and self.wind_velocity_y is not None:
            print(f"Applying constant wind from initialization: X={self.wind_velocity_x:.2f} m/s, Y={self.wind_velocity_y:.2f} m/s")
            self.set_custom_wind(self.wind_velocity_x, self.wind_velocity_y)

    def set_custom_wind(self, wind_velocity_x, wind_velocity_y):
        """
        Set custom constant wind velocities, completely bypassing atmospheric model.
        
        Args:
            wind_velocity_x (float): Wind velocity in X (East-West) direction (m/s)
            wind_velocity_y (float): Wind velocity in Y (North-South) direction (m/s)
        """
        print(f"Setting custom constant wind: X={wind_velocity_x:.2f} m/s, Y={wind_velocity_y:.2f} m/s")
        
        # Create a completely custom atmosphere with ONLY wind parameters
        # No temperature, pressure, or other atmospheric data - just constant wind
        try:
            # Set atmospheric model to custom with only wind parameters
            # Temperature and pressure will use defaults
            self.environment.set_atmospheric_model(
                type="custom_atmosphere",
                temperature=lambda h: 300,  # Constant 300K temperature
                wind_u=lambda h: wind_velocity_x,  # Constant X wind
                wind_v=lambda h: wind_velocity_y   # Constant Y wind
            )
            print(f"Custom constant wind applied successfully")
        except Exception as e:
            print(f"Error setting custom wind: {e}")
            print("Trying alternative method...")
            
            # Alternative: Create environment with no atmospheric model, then set wind
            try:
                # Don't set any atmospheric model - use defaults
                # Then manually set wind attributes if they exist
                self.environment.set_atmospheric_model(type="standard_atmosphere")
                
                # Override wind methods directly
                self.environment.wind_velocity_x = lambda h: wind_velocity_x
                self.environment.wind_velocity_y = lambda h: wind_velocity_y
                print(f"Wind set via direct attribute override")
            except Exception as e2:
                print(f"Error with alternative method: {e2}")
        
        # Recreate Flight with updated environment
        self.flight = Flight(
            rocket=self.rocket, 
            environment=self.environment, 
            rail_length=5.2,
            inclination=self.ramp_inclinaison, 
            heading=self.heading
        )
        
        print("Flight simulation recreated with constant wind.")
    
    def get_wind_at_altitude(self, altitude=500):
        """
        Get the wind velocity at a specific altitude from the environment.
        Useful for verifying that custom wind was applied correctly.
        
        Args:
            altitude (float): Altitude in meters
            
        Returns:
            tuple: (wind_x, wind_y) in m/s
        """
        try:
            # Try to get wind from environment
            if hasattr(self.environment, 'wind_velocity_x') and callable(self.environment.wind_velocity_x):
                wind_x = self.environment.wind_velocity_x(altitude)
            else:
                wind_x = 0
                
            if hasattr(self.environment, 'wind_velocity_y') and callable(self.environment.wind_velocity_y):
                wind_y = self.environment.wind_velocity_y(altitude)
            else:
                wind_y = 0
                
            return (wind_x, wind_y)
        except Exception as e:
            print(f"Could not extract wind: {e}")
            return (0, 0)


    def plot_flight(self, trajectory_filepath=None, kml_filepath=None, show_plots=True, wind_filepath=None):
        """
        Robust flight plotting and data export.
        """
        # 1. Plotting (Optional)
        if show_plots:
            try:
                self.flight.plots.trajectory_3d()
            except Exception as e:
                print(f"Could not plot 3D trajectory: {e}")

        # 2. KML Export
        kml_name = kml_filepath if kml_filepath else "trajectory.kml"
        try:
            FlightDataExporter(self.flight).export_kml(
                file_name=kml_name, extrude=True, altitude_mode="relativetoground"
            )
        except Exception as e:
            print(f"KML Export failed: {e}")

        # 3. Manual CSV Export (Fixes 'ndarray not callable' error)
        traj_name = trajectory_filepath if trajectory_filepath else "flight_data.csv"

        try:
            # Get time array (handles different RocketPy versions)
            t_data = self.flight.time

            # Helper to safely extract data columns
            def get_col(name, ref_len):
                val = getattr(self.flight, name, None)
                if val is None: return np.zeros(ref_len)

                # If it's a function (New RocketPy), call it
                if callable(val):
                    return val(t_data)
                # If it's an array (Old RocketPy), return it
                elif isinstance(val, np.ndarray):
                    return val
                # If it's a scalar, fill an array
                else:
                    return np.full(ref_len, val)

            # Create DataFrame manually
            df = pd.DataFrame({
                "time": t_data,
                "x": get_col("x", len(t_data)),
                "y": get_col("y", len(t_data)),
                "z": get_col("z", len(t_data)),
                "wind_velocity_x": get_col("wind_velocity_x", len(t_data)),
                "wind_velocity_y": get_col("wind_velocity_y", len(t_data)),
            })
            df.to_csv(traj_name, index=False)

        except Exception as e:
            print(f"CSV Export failed: {e}")
            import traceback
            traceback.print_exc()

    def is_stable(self):
        """
        Checks stability safely.
        """
        try:
            burnout_time = self.motor.burn_out_time

            # Calculate static margin
            # Note: static_margin might return a float, an array, or a function depending on version
            margin_fn = self.rocket.static_margin

            if callable(margin_fn):
                val = margin_fn(burnout_time)
            else:
                val = margin_fn  # It was already a value

            # Handle if result is a 1-element array
            if isinstance(val, np.ndarray):
                val = float(val)

            # Check limits
            if val > 1.0:
                return True
            return False

        except Exception as e:
            # If calculation fails, assume unstable
            return False