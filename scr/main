"""
Color Sorting Pick & Place Robot — Main Controller
CoppeliaSim + Python ZMQ Remote API

Usage:
    1. Open CoppeliaSim and load scenes/color_sort.ttt
    2. Press Play in CoppeliaSim
    3. Run: python src/main.py
"""

import time
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'zmqRemoteApi'))

from robot_controller import RobotController
from color_detector import ColorDetector

# ── Configuration ──────────────────────────────────────────────────────────────
PICKUP_ZONE    = [0.0, 0.5, 0.05]   # Where blocks arrive from conveyor
HOVER_HEIGHT   = 0.15               # Height above target before descend
MOTION_DELAY   = 1.2                # Seconds to wait for IK motion

# Drop positions for each color bin (x, y, z)
DROP_ZONES = {
    'red':   [ 0.50, -0.40, 0.05],
    'green': [ 0.50,  0.00, 0.05],
    'blue':  [ 0.50,  0.40, 0.05],
}
# ───────────────────────────────────────────────────────────────────────────────


def hover_above(pos, height=HOVER_HEIGHT):
    """Return a position directly above a given XYZ."""
    return [pos[0], pos[1], pos[2] + height]


def run_sorting_loop(robot: RobotController, detector: ColorDetector):
    print("[INFO] Color sorting loop started. Press Ctrl+C to stop.\n")
    sorted_counts = {'red': 0, 'green': 0, 'blue': 0}

    while True:
        # ── 1. Wait for a block at the pickup sensor ───────────────────────
        block_handle = robot.wait_for_block()
        if block_handle is None:
            time.sleep(0.05)
            continue

        block_pos = robot.get_object_position(block_handle)
        print(f"[INFO] Block detected at {block_pos}")

        # ── 2. Detect color via vision sensor ─────────────────────────────
        color = detector.detect_color()
        if color not in DROP_ZONES:
            print(f"[WARN] Unknown color '{color}', skipping block.")
            continue
        print(f"[INFO] Detected color: {color.upper()}")

        # ── 3. Pick ────────────────────────────────────────────────────────
        robot.move_to(hover_above(block_pos))       # hover above
        robot.move_to(block_pos)                    # descend
        robot.grasp(block_handle)                   # attach block
        robot.move_to(hover_above(block_pos))       # lift

        # ── 4. Transport ───────────────────────────────────────────────────
        drop_pos = DROP_ZONES[color]
        robot.move_to(hover_above(drop_pos))        # hover over bin
        robot.move_to(drop_pos)                     # lower into bin

        # ── 5. Place ───────────────────────────────────────────────────────
        robot.release()                             # detach block
        robot.move_to(hover_above(drop_pos))        # retract

        # ── 6. Return to home ─────────────────────────────────────────────
        robot.go_home()

        sorted_counts[color] += 1
        print(f"[OK]  Placed {color} block. Totals: {sorted_counts}\n")


def main():
    print("=" * 55)
    print("  CoppeliaSim Color Sorting Pick & Place Robot")
    print("=" * 55)

    robot    = RobotController(motion_delay=MOTION_DELAY)
    detector = ColorDetector(robot.sim)

    try:
        robot.connect()
        robot.start_simulation()
        run_sorting_loop(robot, detector)
    except KeyboardInterrupt:
        print("\n[INFO] Stopping simulation...")
    finally:
        robot.stop_simulation()
        robot.disconnect()
        print("[INFO] Done.")


if __name__ == '__main__':
    main()
