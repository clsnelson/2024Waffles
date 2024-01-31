from phoenix6.configs.talon_fx_configs import InvertedValue, NeutralModeValue, TalonFXConfiguration
from phoenix6.hardware.talon_fx import TalonFX


class DriverController:
    port = 0
    deadband = 0.15

class Waffles:
    k_wheel_size = 0.1 # meters
    k_max_speed = 3.658 # m/s
    k_max_rot_rate = 10.472 # rad/s
    k_drive_base_radius = 0.43 # meters
    
class DriveMotorConstants:
    """Constants for a TalonFX drive motor for a swerve module."""
    
    def __init__(self, motor_id: int, 
                 k_s: float=0.24, k_v: float=0.12, k_a: float=0, k_p: float=3, k_i: float=0, k_d: float=0, inverted: InvertedValue=InvertedValue.COUNTER_CLOCKWISE_POSITIVE) -> None:
        
        self.motor_id = motor_id
        
        self.k_s = k_s
        self.k_v = k_v
        self.k_a = k_a
        self.k_p = k_p
        self.k_i = k_i
        self.k_d = k_d
        
        self.inverted = inverted
        
        self.neutral_mode = NeutralModeValue.BRAKE
        
    def apply_configuration(self, motor: TalonFX) -> TalonFX:
        """Applies the DriveMotorConstants into the TalonFX.

        Args:
            motor (TalonFX): The drive motor to apply the constants to.

        Returns:
            TalonFX: The new configurated TalonFX for method chaining.
        """
        config = TalonFXConfiguration()
        config.slot0.with_k_s(self.k_s).with_k_v(self.k_v).with_k_a(self.k_a).with_k_p(self.k_p).with_k_i(self.k_i).with_k_d(self.k_d)
        config.motor_output.with_neutral_mode(self.neutral_mode).with_inverted(self.inverted)
        config.feedback.sensor_to_mechanism_ratio = k_drive_gear_ratio
        motor.configurator.apply(config)
        return motor
        
class DirectionMotorConstants:
    
    def __init__(self, motor_id: int, 
                 k_s: float=0.25, cruise_velocity: int=60, cruise_acceleration: int=160, cruise_jerk: int=1600, 
                 k_v: float=0.1, k_a: float=0, k_p: float=0.78, k_i: float=0, k_d: float=0.0004) -> None:
        
        self.motor_id = motor_id
        
        self.k_s = k_s
        self.k_v = k_v
        self.k_a = k_a
        self.k_p = k_p
        self.k_i = k_i
        self.k_d = k_d
        
        self.cruise_velocity = cruise_velocity
        self.cruise_acceleration = cruise_acceleration
        self.cruise_jerk = cruise_jerk
        
        self.neutral_mode = NeutralModeValue.COAST
        self.invert = InvertedValue.CLOCKWISE_POSITIVE
        
    def apply_configuration(self, motor: TalonFX) -> TalonFX:
        """Applies the DriveMotorConstants into the TalonFX.

        Args:
            motor (TalonFX): The drive motor to apply the constants to.

        Returns:
            TalonFX: The new configurated TalonFX for method chaining.
        """
        config = TalonFXConfiguration()
        config.slot0.with_k_s(self.k_s).with_k_v(self.k_v).with_k_a(self.k_a).with_k_p(self.k_p).with_k_i(self.k_i).with_k_d(self.k_d)
        config.motor_output.with_neutral_mode(self.neutral_mode).with_inverted(self.invert)
        config.motion_magic.with_motion_magic_cruise_velocity(self.cruise_velocity).with_motion_magic_acceleration(self.cruise_acceleration).with_motion_magic_jerk(self.cruise_jerk)
        config.closed_loop_general.continuous_wrap = True
        config.feedback.sensor_to_mechanism_ratio = k_direction_gear_ratio
        motor.configurator.apply(config)
        return motor
        
class MotorIDs:
    LEFT_FRONT_DRIVE = 0
    LEFT_REAR_DRIVE = 1
    RIGHT_FRONT_DRIVE = 2
    RIGHT_REAR_DRIVE = 3

    LEFT_FRONT_DIRECTION = 4
    LEFT_REAR_DIRECTION = 5
    RIGHT_FRONT_DIRECTION = 6
    RIGHT_REAR_DIRECTION = 7

class CANIDs:
    LEFT_FRONT = 10
    RIGHT_FRONT = 12
    LEFT_REAR = 11
    RIGHT_REAR = 13

k_direction_gear_ratio = 150 / 7
k_drive_gear_ratio = 27 / 4
