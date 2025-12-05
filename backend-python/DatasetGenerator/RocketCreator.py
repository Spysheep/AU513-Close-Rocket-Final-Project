import numpy as np
from rocketpy import Environment,Rocket,Flight
from rocketpy.simulation import FlightDataExporter
import motor_closed_rocket as mc
import datetime

class RocketCreator:
    def __init__(self,delay=0,heading = 220,ramp_inclinaison = 85,motor_name = "Pro75M1670",radius = 127 / 2000,mass = 14.426,inertia = (6.321, 6.321, 0.034),center_of_mass_without_motor=1,cone_length = 0.55829, rocket_length = 2.533, fin_cat = "trapezoidal",number_of_ailerons = 4,root_chord=0.120,tip_chord=0.060,span=0.110,fins_pos = 0,fin_inclinaison = 0.5,drag_coeff = 1.0,trigger = "apogee"):
        # Constant
        self.EARTH_RADIUS = 6371000
        self.latitude_0 = 43.242222
        self.longitude_0 = -0.030556
        self.altitude_0 = 409
        self.r = self.EARTH_RADIUS + self.altitude_0


        # Exported variables
            # Initial position :
        self.x0 = self.r * np.cos(self.latitude_0) * np.cos(self.longitude_0)
        self.y0 = self.r * np.cos(self.latitude_0) * np.sin(self.longitude_0)
        self.z0 = self.r * np.sin(self.latitude_0)
            # Ramp info :
        self.heading = heading
        self.ramp_inclinaison = ramp_inclinaison
            # Wind data :
        self.wind_csv_files = "wind_data.csv"
        self.wind_header = ["z","wind_velocity_x","wind_velocity_y"]
            # Motor data :
        self.motor_name = motor_name
            # Rocket data :
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


        # Environment variables
        self.environment = Environment(latitude=self.latitude_0, longitude=0, elevation=self.altitude_0)
        self.date = datetime.date.today() + datetime.timedelta(days=delay)
        self.environment.set_date((self.date.year, self.date.month, self.date.day, 12))
        self.environment.set_atmospheric_model(type="forecast", file="GFS")

        # Motor variables
        motor = mc.MotorClosedRocket()
        self.motor = motor.get_motor(motor_name)

        # Rocket variables
        self.rocket = Rocket(
            radius = self.radius,
            mass = self.mass,
            inertia=self.inertia,
            power_off_drag="data/rocket/calisto/powerOffDragCurve.csv", # à changer
            power_on_drag="data/rocket/calisto/powerOnDragCurve.csv", # à changer
            center_of_mass_without_motor=self.center_of_mass_without_motor,
            coordinate_system_orientation="tail_to_nose",
        )
        self.rocket.add_motor(self.motor,position=0)

        # Add nose
        self.nose_cone = self.rocket.add_nose(
            length=self.cone_length, kind="von karman", position=self.rocket_length
        )

        # Add fins
        self.fin_set = None
        if fin_cat == "trapezoidal":
            self.fin_set = self.rocket.add_trapezoidal_fins(
                n=self.number_of_fins,
                root_chord=self.root_chord,
                tip_chord=self.tip_chord,
                span=self.span,
                position=self.fins_pos + self.root_chord,
                cant_angle=self.fin_inclinaison,
                airfoil=("data/airfoils/NACA0012-radians.txt", "radians"),
            )
        elif fin_cat == "elyptique":
            self.fin_set = self.rocket.add_elliptical_fins(
                n=self.number_of_fins,
                root_chord=self.root_chord,
                span=self.span,
                position=self.fins_pos+ self.root_chord,
                cant_angle=self.fin_inclinaison,
                airfoil=("data/airfoils/NACA0012-radians.txt", "radians"),
            )

        self.tail = self.rocket.add_tail(
            top_radius=self.radius, bottom_radius=self.radius-0.02, length=0, position=0
        )

        self.para = self.rocket.add_parachute(
            name="para",
            cd_s=self.drag_coeff,
            trigger=self.trigger,  # ejection at apogee
        )

        # Flight variables
        self.flight = Flight(rocket=self.rocket, environment=self.environment, rail_length=5.2, inclination=self.ramp_inclinaison, heading=self.heading)
        self.flight.env.longitude = self.longitude_0

    def plot_flight(self, trajectory_filepath=None, kml_filepath=None, show_plots=True, wind_filepath=None):
        """
        Plots the flight and exports data.
        If filepaths are provided, data is saved to them.
        Set show_plots=False to disable popping up 3D plot windows.
        """

        # 1. Plotting
        if show_plots:
            self.flight.plots.trajectory_3d()

            # 2. KML Export
        # Use the provided kml_filepath, or default to "trajectory.kml"
        kml_name = kml_filepath if kml_filepath else "trajectory.kml"
        FlightDataExporter(self.flight).export_kml(
            file_name=kml_name,
            extrude=True,
            altitude_mode="relativetoground",
        )

        exporter = FlightDataExporter(self.flight)

        # 3. Trajectory CSV Export (The part you care about)
        # Use the provided trajectory_filepath, or default to "flight_data.csv"
        traj_name = trajectory_filepath if trajectory_filepath else "flight_data.csv"

        # --- KEY CHANGE ---
        # Added 't' to match the data you were saving in dataset_generator.py
        exporter.export_data(traj_name, "x", "y", "z")

        # 4. Wind Data Export (Keeps original behavior)
        # This will just overwrite "wind_data.csv" every time, which is fine.
        wind_name = wind_filepath if wind_filepath else "wind_data.csv"
        exporter.export_data(wind_name, "z", "wind_velocity_x", "wind_velocity_y")

    def is_stable(self):
        burnout_time = self.motor.burn_out_time
        self.min_static_margin = self.rocket.static_margin(burnout_time)
        # print(self.min_static_margin)
        if self.min_static_margin > 1:
            return True
        else:
            return False

