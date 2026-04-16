"""
robot_controller.py
Handles all CoppeliaSim communication: connection, IK motion, gripper, sensors.
"""

import time
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'zmqRemoteApi'))

try:
    from zmqRemoteApi import RemoteAPIClient
except ImportError:
    raise ImportError(
        "ZMQ Remote API not found.\n"
        "Copy the zmqRemoteApi folder from:\n"
        "  <CoppeliaSim>/programming/zmqRemoteApi/clients/python/src/\n"
        "into src/zmqRemoteApi/"
    )


class RobotController:
    """
    Controls a robot arm in CoppeliaSim via ZMQ Remote API.

    Object names expected in your .ttt scene:
        /UR5              — robot arm root
        /UR5/ikTarget     — IK target dummy (drives end-effector)
        /UR5/gripper      — gripper model root
        /ProxSensor       — proximity sensor at conveyor pickup zone
        /VisionSensor     — vision sensor above conveyor
        /ConveyorBelt     — conveyor joint/motor

    Adjust these names to match your actual scene hierarchy.
    """

    SCENE_OBJECTS = {
        'robot':         '/UR5',
        'ik_target':     '/UR5/ikTarget',
        'gripper':       '/UR5/gripper',
        'prox_sensor':   '/ProxSensor',
        'vision_sensor': '/VisionSensor',
        'conveyor':      '/ConveyorBelt',
    }

    HOME_JOINT_ANGLES = [0, -30, 60, -30, -90, 0]   # degrees

    def __init__(self, host='localhost', port=23000, motion_delay=1.2):
        self.host         = host
        self.port         = port
        self.motion_delay = motion_delay
        self.client       = None
        self.sim          = None
        self.handles      = {}
        self._grasped     = None

    # ── Connection ─────────────────────────────────────────────────────────────

    def connect(self):
        print(f"[INFO] Connecting to CoppeliaSim at {self.host}:{self.port} ...")
        self.client = RemoteAPIClient(host=self.host, port=self.port)
        self.sim    = self.client.getObject('sim')
        print("[INFO] Connected.")
        self._get_handles()

    def disconnect(self):
        self.client = None
        self.sim    = None
        print("[INFO] Disconnected.")

    def _get_handles(self):
        for name, path in self.SCENE_OBJECTS.items():
            try:
                self.handles[name] = self.sim.getObject(path)
                print(f"  [OK] Handle: {name} → {path}")
            except Exception:
                print(f"  [WARN] Object not found in scene: {path}")
                self.handles[name] = None

    # ── Simulation lifecycle ───────────────────────────────────────────────────

    def start_simulation(self):
        state = self.sim.getSimulationState()
        if state == self.sim.simulation_stopped:
            self.sim.startSimulation()
            time.sleep(1.0)
            print("[INFO] Simulation started.")
        else:
            print("[INFO] Simulation already running.")

    def stop_simulation(self):
        self.sim.stopSimulation()
        print("[INFO] Simulation stopped.")

    # ── Motion ─────────────────────────────────────────────────────────────────

    def move_to(self, position, orientation=None):
        """
        Move robot end-effector to world-space XYZ by repositioning the IK target.
        CoppeliaSim IK solver handles joint angles automatically.

        Args:
            position    : [x, y, z] in meters (world frame)
            orientation : [alpha, beta, gamma] Euler angles (radians). 
                          If None, keeps current orientation.
        """
        target = self.handles.get('ik_target')
        if target is None:
            print("[ERROR] IK target handle not found.")
            return

        self.sim.setObjectPosition(target, self.sim.handle_world, position)

        if orientation is not None:
            self.sim.setObjectOrientation(target, self.sim.handle_world, orientation)

        time.sleep(self.motion_delay)

    def go_home(self):
        """Move all joints to home configuration."""
        robot = self.handles.get('robot')
        if robot is None:
            return
        import math
        for i, angle_deg in enumerate(self.HOME_JOINT_ANGLES):
            try:
                joint = self.sim.getObject(f'/UR5/joint{i+1}')
                self.sim.setJointTargetPosition(joint, math.radians(angle_deg))
            except Exception:
                pass
        time.sleep(self.motion_delay * 1.5)

    # ── Gripper ────────────────────────────────────────────────────────────────

    def grasp(self, object_handle):
        """Attach an object to the gripper (kinematic attachment)."""
        gripper = self.handles.get('gripper')
        if gripper is None:
            print("[WARN] No gripper handle — using direct parent attachment.")
            gripper = self.handles.get('robot')

        self.sim.setObjectParent(object_handle, gripper, True)
        self._grasped = object_handle
        print(f"  [GRIP] Grasped object handle {object_handle}")

    def release(self):
        """Detach the currently held object, leaving it in world space."""
        if self._grasped is not None:
            self.sim.setObjectParent(self._grasped, -1, True)
            print(f"  [GRIP] Released object handle {self._grasped}")
            self._grasped = None

    # ── Sensing ────────────────────────────────────────────────────────────────

    def wait_for_block(self, timeout=30.0):
        """
        Poll proximity sensor until a block is detected or timeout.
        Returns the detected object handle, or None on timeout.
        """
        sensor = self.handles.get('prox_sensor')
        if sensor is None:
            return None

        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                result = self.sim.readProximitySensor(sensor)
                # result = (detectionState, distance, point, objectHandle, normalVector)
                if isinstance(result, (list, tuple)) and len(result) >= 4:
                    detected, *_, obj_handle, _ = result
                    if detected == 1 and obj_handle > 0:
                        return obj_handle
                elif result == 1:
                    return -1   # detected but no specific handle
            except Exception as e:
                print(f"[WARN] Sensor read error: {e}")
            time.sleep(0.05)
        return None

    def get_object_position(self, handle):
        """Return [x, y, z] world position of an object."""
        return self.sim.getObjectPosition(handle, self.sim.handle_world)

    # ── Conveyor ───────────────────────────────────────────────────────────────

    def set_conveyor_speed(self, speed=0.1):
        """Set conveyor belt velocity (m/s)."""
        conveyor = self.handles.get('conveyor')
        if conveyor is not None:
            self.sim.setJointTargetVelocity(conveyor, speed)

    def stop_conveyor(self):
        self.set_conveyor_speed(0.0)

    def resume_conveyor(self, speed=0.1):
        self.set_conveyor_speed(speed)
