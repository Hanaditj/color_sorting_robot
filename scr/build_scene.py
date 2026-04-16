"""
build_scene.py
Programmatically builds the CoppeliaSim color-sorting scene via ZMQ API.

Run this ONCE with CoppeliaSim open and NO scene loaded:
    python src/build_scene.py

It will create and position:
  • A conveyor belt (primitive joint + surface)
  • A proximity sensor at the pickup zone
  • A vision sensor above the pickup zone
  • A UR5 robot arm (from model library)
  • Three colored destination bins
  • A spawn-point dummy

After running, save the scene as: scenes/color_sort.ttt
"""

import sys, os, time, math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'zmqRemoteApi'))

try:
    from zmqRemoteApi import RemoteAPIClient
except ImportError:
    raise ImportError("Copy zmqRemoteApi client into src/zmqRemoteApi/")


def build_scene():
    print("[Build] Connecting to CoppeliaSim ...")
    client = RemoteAPIClient()
    sim    = client.getObject('sim')
    print("[Build] Connected.\n")

    sim.stopSimulation()
    time.sleep(0.5)

    # ── 1. Conveyor surface (static box as visual stand-in) ────────────────
    print("[Build] Creating conveyor ...")
    conveyor = sim.createPureShape(
        0,      # cuboid
        1+2,    # static + visible
        [1.0, 0.2, 0.02],   # length × width × thickness
        0, None
    )
    sim.setObjectPosition(conveyor, sim.handle_world, [0.0, 0.5, 0.01])
    sim.setShapeColor(conveyor, None, sim.colorcomponent_ambient_diffuse, [0.3, 0.3, 0.3])
    sim.setObjectAlias(conveyor, 'ConveyorSurface')

    # Conveyor joint (velocity-controlled for belt motion)
    conveyor_joint = sim.createJoint(
        sim.joint_prismatic_subtype, sim.jointmode_velocity, 0, [None, None]
    )
    sim.setObjectAlias(conveyor_joint, 'ConveyorBelt')
    sim.setObjectPosition(conveyor_joint, sim.handle_world, [0.0, 0.5, 0.02])

    # ── 2. Proximity sensor at pickup zone ─────────────────────────────────
    print("[Build] Creating proximity sensor ...")
    prox = sim.createProximitySensor(
        sim.proximitysensor_cylinder_subtype,
        sim.objectspecialproperty_detectable_all,
        0,
        [0.0, 0.0, 0.05,  0.0, 0.0, 0.0,  0.05, 0.1, 0, 0, 0, 0, 0, 0, 0]
    )
    sim.setObjectAlias(prox, 'ProxSensor')
    sim.setObjectPosition(prox, sim.handle_world, [0.0, 0.5, 0.08])
    sim.setObjectOrientation(prox, sim.handle_world, [math.pi, 0, 0])

    # ── 3. Vision sensor above pickup zone ─────────────────────────────────
    print("[Build] Creating vision sensor ...")
    vision = sim.createVisionSensor(
        0,
        [64, 64],
        [0.01, 10.0, 60 * math.pi / 180, 0, 0.5, 0.5, 0, 0, 0, 0, 0, 0]
    )
    sim.setObjectAlias(vision, 'VisionSensor')
    sim.setObjectPosition(vision, sim.handle_world, [0.0, 0.5, 0.40])
    sim.setObjectOrientation(vision, sim.handle_world, [math.pi, 0, 0])

    # ── 4. Spawn point dummy ───────────────────────────────────────────────
    spawn = sim.createDummy(0.02, None)
    sim.setObjectAlias(spawn, 'SpawnPoint')
    sim.setObjectPosition(spawn, sim.handle_world, [-0.45, 0.5, 0.04])

    # ── 5. Colored destination bins ────────────────────────────────────────
    print("[Build] Creating color bins ...")
    bins_config = [
        ('BinRed',   [1.0, 0.1, 0.1], [ 0.5, -0.40, 0.0]),
        ('BinGreen', [0.1, 0.8, 0.1], [ 0.5,  0.00, 0.0]),
        ('BinBlue',  [0.1, 0.3, 1.0], [ 0.5,  0.40, 0.0]),
    ]
    for name, color, pos in bins_config:
        bin_h = sim.createPureShape(0, 1+2, [0.12, 0.12, 0.08], 0, None)
        sim.setObjectAlias(bin_h, name)
        sim.setObjectPosition(bin_h, sim.handle_world, pos)
        sim.setShapeColor(bin_h, None, sim.colorcomponent_ambient_diffuse, color)

    # ── 6. IK Target dummy (end-effector target) ───────────────────────────
    ik_target = sim.createDummy(0.03, None)
    sim.setObjectAlias(ik_target, 'IKTarget')
    sim.setObjectPosition(ik_target, sim.handle_world, [0.0, 0.3, 0.4])

    # ── 7. Floor ───────────────────────────────────────────────────────────
    floor = sim.createPureShape(0, 1+2, [2.0, 2.0, 0.01], 0, None)
    sim.setObjectAlias(floor, 'Floor')
    sim.setObjectPosition(floor, sim.handle_world, [0.0, 0.0, -0.005])
    sim.setShapeColor(floor, None, sim.colorcomponent_ambient_diffuse, [0.6, 0.6, 0.6])

    print("""
[Build] ✅ Scene built successfully!

NEXT STEPS:
  1. In CoppeliaSim: Add a UR5 robot from the Model Browser
     (Models → robots → non-mobile → UR5)
  2. Position the UR5 at approximately [0.0, 0.0, 0.0]
  3. Add the Lua script (scripts/color_sort_scene.lua) as a child
     script on a dummy called 'SceneManager'
  4. Attach the IK script to UR5 using the kinematics module
  5. Save as: scenes/color_sort.ttt
  6. Run: python src/main.py
""")


if __name__ == '__main__':
    build_scene()
