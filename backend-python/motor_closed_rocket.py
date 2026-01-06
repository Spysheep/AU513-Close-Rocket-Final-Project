from rocketpy import SolidMotor

class MotorClosedRocket:
    def __init__(self):
        self.motor = None

    def get_motor(self,motor_name):
        if motor_name == "Pro54-5G Barasinga":
            # Pro54-5G - BARASINGA : 2060K570-17A
            self.motor = SolidMotor(
                thrust_source="data/motors/cesaroni/Cesaroni_Pro54-5G_BARASINGA.eng",
                dry_mass=0.65,
                dry_inertia=(0.125, 0.125, 0.002), # <-- ATTENTION: Valeur non connue
                nozzle_radius=(37.4 / 2) / 1000, # 18.7 mm (basé sur ⌀ 37.4 de l'image)
                grain_number=5,
                grain_density=1815,
                grain_outer_radius=22.5 / 1000,
                grain_initial_inner_radius=15 / 1000,
                grain_initial_height=80 / 1000,
                grain_separation=5 / 1000,
                center_of_dry_mass_position=0.248,
                grains_center_of_mass_position=0.241,
                nozzle_position=0,
                burn_time=3.59,
                throat_radius=(31.8 / 2) / 1000,
                coordinate_system_orientation="nozzle_to_combustion_chamber"
            )
        elif motor_name == "Pro75-3G":
            # Pro75-3G : 2060K570-17A
            self.motor = SolidMotor(
                thrust_source="data/motors/cesaroni/Cesaroni_Pro75-3G.eng",
                dry_mass=1.638,
                dry_inertia=(0.125, 0.125, 0.002),  # <-- ATTENTION: Valeur non connue
                nozzle_radius=(47.62 / 2) / 1000,
                grain_number=3,
                grain_density=1815,
                grain_outer_radius=10 / 1000,
                grain_initial_inner_radius=5 / 1000,
                grain_initial_height=30 / 1000,
                grain_separation=2 / 1000,
                grains_center_of_mass_position=0.243,
                center_of_dry_mass_position=0.243,
                nozzle_position=0,
                burn_time=4.68,
                throat_radius=(79.32 / 2) / 1000,
                coordinate_system_orientation="nozzle_to_combustion_chamber"
            )
        elif motor_name == "Pro24-6G":
            # Pro24-6G : 2060K570-17A
            self.motor = SolidMotor(
                thrust_source="data/motors/cesaroni/Cesaroni_Pro24-6G.eng",
                dry_mass=0.0843,
                dry_inertia=(0.0005, 0.0005, 0.00001),
                nozzle_radius=(23.8 / 2) / 1000,
                grain_number=6,
                grain_density=1815,
                grain_outer_radius=22.5 / 1000,
                grain_initial_inner_radius=15 / 1000,
                grain_initial_height=80 / 1000,
                grain_separation=5 / 1000,
                grains_center_of_mass_position=0.114,
                center_of_dry_mass_position=0.114,
                nozzle_position=0,
                burn_time=1.01,
                throat_radius=(35.4 / 2) / 1000,
                coordinate_system_orientation="nozzle_to_combustion_chamber"
            )
        elif motor_name == "Pro75M1670":
            self.motor = SolidMotor(
                thrust_source="data/motors/cesaroni/Cesaroni_M1670.eng",
                dry_mass=1.815,
                dry_inertia=(0.125, 0.125, 0.002),
                nozzle_radius=33 / 1000,
                grain_number=5,
                grain_density=1815,
                grain_outer_radius=33 / 1000,
                grain_initial_inner_radius=15 / 1000,
                grain_initial_height=120 / 1000,
                grain_separation=5 / 1000,
                grains_center_of_mass_position=0.397,
                center_of_dry_mass_position=0.317,
                nozzle_position=0,
                burn_time=3.9,
                throat_radius=11 / 1000,
                coordinate_system_orientation="nozzle_to_combustion_chamber",
            )
        else:
            raise ValueError("Motor not found")
        return self.motor
    def get_motor_nozzle_length(self):
        return self.motor.nozzle_length