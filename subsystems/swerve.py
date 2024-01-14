import math

import navx
from commands2 import Command, CommandScheduler, Subsystem
from pathplannerlib.auto import AutoBuilder, PathPlannerAuto
from pathplannerlib.config import (HolonomicPathFollowerConfig, PIDConstants,
                                   ReplanningConfig)
from phoenix5 import *
from phoenix5.sensors import CANCoder, SensorInitializationStrategy
from wpilib import DriverStation, Field2d, RobotBase, SmartDashboard
from wpimath.controller import PIDController
from wpimath.geometry import Pose2d, Rotation2d, Translation2d
from wpimath.kinematics import (ChassisSpeeds, SwerveDrive4Kinematics,
                                SwerveDrive4Odometry, SwerveModulePosition,
                                SwerveModuleState)

from constants import *


class SwerveModule(Subsystem):
    """
    Takes inputted SwerveModuleStates and moves the direction and drive motor to the selected positions.

    The direction motor rotates the wheel into position.
    The drive motor spins the wheel to move.
    """

    def __init__(self, moduleName: str, directionMotorControllerID: int, driveMotorControllerID: int, CANCoderID: int, offset: float) -> None:
        super().__init__()

        self.moduleName = moduleName

        self.turningEncoder = CANCoder(CANCoderID)
        self.turningEncoder.configSensorInitializationStrategy(SensorInitializationStrategy.BootToAbsolutePosition, Motor.kTimeoutMs)
        self.turningEncoder.configSensorDirection(True, Motor.kTimeoutMs)
        self.turningEncoder.configMagnetOffset(offset, Motor.kTimeoutMs)

        self.directionMotor = TalonFX(directionMotorControllerID)
        self.directionMotor.configSelectedFeedbackSensor(FeedbackDevice.IntegratedSensor, 0, Motor.kTimeoutMs)
        self.directionMotor.selectProfileSlot(Motor.kSlotIdx, Motor.kPIDLoopIdx)
        
        self.directionMotor.config_kP(Motor.kSlotIdx, DirectionMotor.kP, Motor.kTimeoutMs)
        self.directionMotor.config_kI(Motor.kSlotIdx, DirectionMotor.kI, Motor.kTimeoutMs)
        self.directionMotor.config_kD(Motor.kSlotIdx, DirectionMotor.kD, Motor.kTimeoutMs)
        self.directionMotor.config_kF(Motor.kSlotIdx, DirectionMotor.kF, Motor.kTimeoutMs)
        self.directionMotor.configMotionCruiseVelocity(DirectionMotor.kCruiseVel, Motor.kTimeoutMs)
        self.directionMotor.configMotionAcceleration(DirectionMotor.kCruiseAccel, Motor.kTimeoutMs)

        #self.directionMotor.configVoltageCompSaturation(Motor.kVoltCompensation, Motor.kTimeoutMs)
        self.directionMotor.setInverted(False)
        self.directionMotor.setNeutralMode(NeutralMode.Brake)

        self.driveMotor = TalonFX(driveMotorControllerID)
        self.driveMotor.configSelectedFeedbackSensor(FeedbackDevice.IntegratedSensor, 0, Motor.kTimeoutMs)
        self.driveMotor.selectProfileSlot(Motor.kSlotIdx, Motor.kPIDLoopIdx)

        self.driveMotor.config_kP(Motor.kSlotIdx, DriveMotor.kP, Motor.kTimeoutMs)
        self.driveMotor.config_kI(Motor.kSlotIdx, DriveMotor.kI, Motor.kTimeoutMs)
        self.driveMotor.config_kD(Motor.kSlotIdx, DriveMotor.kD, Motor.kTimeoutMs)

        self.driveMotor.configVoltageCompSaturation(Motor.kVoltCompensation, Motor.kTimeoutMs)
        self.driveMotor.setInverted(False)
        self.driveMotor.setNeutralMode(NeutralMode.Brake)

        CommandScheduler.getInstance().registerSubsystem(self)

    def getAngle(self) -> Rotation2d:
        return Rotation2d.fromDegrees(self.directionMotor.getSelectedSensorPosition() / Motor.kGearRatio * (360/2048))
    
    def resetSensorPostition(self) -> None:
        
        if RobotBase.isReal():
            self.directionMotor.setSelectedSensorPosition(Motor.kGearRatio * (self.turningEncoder.getAbsolutePosition() * (2048 / 360)), Motor.kPIDLoopIdx, Motor.kTimeoutMs)
            self.directionMotor.getSimCollection().setIntegratedSensorRawPosition(int(Motor.kGearRatio * (self.turningEncoder.getAbsolutePosition() * (2048 / 360))))
        else:
            self.directionMotor.setSelectedSensorPosition(0, Motor.kPIDLoopIdx, Motor.kTimeoutMs)
            self.directionMotor.getSimCollection().setIntegratedSensorRawPosition(int(0))

    def getState(self) -> SwerveModuleState:
        # units/100ms -> m/s
        speed = self.driveMotor.getSelectedSensorVelocity() / Motor.kGearRatio * 10 * Larry.kWheelSize * math.pi
        rotation = self.directionMotor.getSelectedSensorPosition() / Motor.kGearRatio * (360/2048)
        return SwerveModuleState(speed, Rotation2d.fromDegrees(rotation))
    
    def getPosition(self) -> SwerveModulePosition:
        return SwerveModulePosition(
            (self.driveMotor.getSelectedSensorPosition() / Motor.kGearRatio) * (Larry.kWheelSize*math.pi),
            self.getAngle()
        )
    
    def periodic(self) -> None:
        #SmartDashboard.putNumber(self.moduleName + "directionAngle", self.getAngle().degrees())
        SmartDashboard.putNumber(self.moduleName + "drivePos", self.driveMotor.getSelectedSensorVelocity())

    def setDesiredState(self, desiredState: SwerveModuleState) -> None:
        currentState = self.getState()
        state = SwerveModuleState.optimize(desiredState, currentState.angle)

        self.driveMotor.set(ControlMode.Velocity, state.speed / (math.pi*Larry.kWheelSize) / 10 * Motor.kGearRatio)
        self.driveMotor.getSimCollection().setIntegratedSensorVelocity(int(state.speed / (math.pi*Larry.kWheelSize) / 10 * Motor.kGearRatio))

        self.changeDirection(state.angle)

    def changeDirection(self, rotation: Rotation2d) -> None:
        angleDiff = rotation.degrees() - self.getAngle().degrees()
        targetAngleDist = math.fabs(angleDiff)

        # When going from x angle to 0, the robot will try and go "the long way around" to the angle. This just checks to make sure we're actually getting the right distance
        if targetAngleDist > 180:
            while targetAngleDist > 180:
                targetAngleDist -= 360
            targetAngleDist = abs(targetAngleDist)

        changeInTalonUnits = targetAngleDist / (360/2048)

        if angleDiff < 0 or angleDiff >= 360:
            angleDiff %= 360
        
        finalPos = self.directionMotor.getSelectedSensorPosition() / Motor.kGearRatio
        if angleDiff > 180:
            # Move CCW
            finalPos -= changeInTalonUnits
        else:
            # Move CW
            finalPos += changeInTalonUnits

        SmartDashboard.putNumber(self.moduleName + "directionPos", finalPos)
        #SmartDashboard.putNumber(self.moduleName + "angle", currentAngle)

        self.directionMotor.set(TalonFXControlMode.MotionMagic, finalPos * Motor.kGearRatio)
        self.directionMotor.getSimCollection().setIntegratedSensorRawPosition(int(finalPos * Motor.kGearRatio))


""""""

class Swerve(Subsystem):
    anglePID = PIDController(0, 0, 0)

    navX = navx.AHRS.create_spi()

    kinematics = SwerveDrive4Kinematics(Translation2d(1, 1), Translation2d(-1, 1),
                                        Translation2d(1, -1), Translation2d(-1, -1)) # LF, LR, RF, RR
    
    field = Field2d()
    
    def __init__(self, leftFront: SwerveModule, leftRear: SwerveModule, rightFront: SwerveModule, rightRear: SwerveModule) -> None:
        super().__init__()

        self.leftFront = leftFront
        self.leftRear = leftRear
        self.rightFront = rightFront
        self.rightRear = rightRear

        self.odometry = SwerveDrive4Odometry(self.kinematics, self.getAngle(),
                                             (self.leftFront.getPosition(), self.leftRear.getPosition(),
                                              self.rightFront.getPosition(), self.rightRear.getPosition()))

        SmartDashboard.putData(self.field)
        SmartDashboard.putData("Reset Odometry", self.resetOdometryCommand())

        self.chassisSpeed = ChassisSpeeds()

        AutoBuilder.configureHolonomic(
            lambda: self.getPose(),
            lambda pose: self.resetOdometry(pose),
            lambda: self.getChassisSpeeds(),
            lambda chassisSpeed: self.drive(chassisSpeed, fieldRelative=False),
            HolonomicPathFollowerConfig(
                PIDConstants(0.0, 0.0, 0.0, 0.0), # translation
                PIDConstants(0.0, 0.0, 0.0, 0.0), # rotation
                Larry.kMaxSpeed,
                Larry.kDriveBaseRadius,
                ReplanningConfig()
            ),
            lambda: self.shouldFlipAutoPath(),
            self
        )

        CommandScheduler.getInstance().registerSubsystem(self)

    def shouldFlipAutoPath(self) -> bool:
        # Flips the PathPlanner path if we're on the red alliance
        return DriverStation.getAlliance() == DriverStation.Alliance.kRed
    
    def runAuto(self, auto: PathPlannerAuto) -> None:
        self.runOnce(lambda: auto)

    def initialize(self) -> None:
        self.leftFront.resetSensorPostition()
        self.leftRear.resetSensorPostition()
        self.rightFront.resetSensorPostition()
        self.rightRear.resetSensorPostition()

    def getAngle(self) -> float:
        return self.navX.getRotation2d()
    
    def drive(self, chassisSpeed:ChassisSpeeds, fieldRelative: bool=True) -> None:
        # Shoutout to team 1706, your code saved our swerve this year lmao
        # Insert function to steady target angle here :)))

        if fieldRelative:
            states = self.kinematics.toSwerveModuleStates(ChassisSpeeds.fromFieldRelativeSpeeds(chassisSpeed, self.getAngle()))
        else:
            states = self.kinematics.toSwerveModuleStates(chassisSpeed)

        desatStates = self.kinematics.desaturateWheelSpeeds(states, Larry.kMaxSpeed)

        self.chassisSpeed = chassisSpeed

        SmartDashboard.putNumberArray("desatedStates", [desatStates[0].angle.degrees(), desatStates[1].angle.degrees(), desatStates[2].angle.degrees(), desatStates[3].angle.degrees()])

        self.setModuleStates(desatStates)

    def getChassisSpeeds(self) -> ChassisSpeeds:
        return self.chassisSpeed

    def setModuleStates(self, moduleStates: tuple[SwerveModuleState, SwerveModuleState, SwerveModuleState, SwerveModuleState]) -> None:
        desatStates = self.kinematics.desaturateWheelSpeeds(moduleStates, Larry.kMaxSpeed)

        self.leftFront.setDesiredState(desatStates[0])
        self.leftRear.setDesiredState(desatStates[1])
        self.rightFront.setDesiredState(desatStates[2])
        self.rightRear.setDesiredState(desatStates[3])

    def getPose(self) -> Pose2d:
        return self.odometry.getPose()

    def resetOdometry(self, pose=Pose2d()) -> None:
        self.odometry.resetPosition(self.getAngle(), (self.leftFront.getPosition(), self.leftRear.getPosition(), self.rightFront.getPosition(), self.rightRear.getPosition()), pose)
        
    def resetOdometryCommand(self) -> Command:
        return self.runOnce(lambda: self.resetOdometry())

    def periodic(self) -> None:
        self.odometry.update(self.getAngle(), (self.leftFront.getPosition(), self.leftRear.getPosition(), self.rightFront.getPosition(), self.rightRear.getPosition()))
        self.field.setRobotPose(self.odometry.getPose())
        SmartDashboard.putNumber("Field X", self.odometry.getPose().X())
        SmartDashboard.putNumber("Field Y", self.odometry.getPose().Y())
        SmartDashboard.putData(self.field)
        