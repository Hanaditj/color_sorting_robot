-- ============================================================
--  ur5_ik.lua
--  Attach as a CHILD SCRIPT on the UR5 robot object.
--
--  Sets up Inverse Kinematics so that moving the /IKTarget
--  dummy automatically drives all 6 UR5 joints.
--  Uses the modern simIK API (CoppeliaSim 4.4+).
-- ============================================================

local ikEnv    = nil
local ikGroup  = nil
local robot    = nil
local ikTarget = nil
local ikTip    = nil
local joints   = {}

function sysCall_init()
    robot    = sim.getObject('.')                  -- the UR5 itself
    ikTarget = sim.getObject('/IKTarget')
    ikTip    = sim.getObject('/UR5/ikTip')         -- tip dummy at end-effector

    -- Collect all 6 joints
    for i = 1, 6 do
        joints[i] = sim.getObject('/UR5/joint' .. i)
    end

    -- ── Set up IK environment ─────────────────────────────────────────────
    ikEnv   = simIK.createEnvironment()
    ikGroup = simIK.createGroup(ikEnv)

    simIK.setGroupCalculation(
        ikEnv, ikGroup,
        simIK.method_damped_least_squares,
        0.05,   -- DLS damping
        300     -- max iterations
    )

    -- Add tip-target constraint (position + orientation)
    simIK.addElementFromScene(
        ikEnv, ikGroup,
        robot, ikTip, ikTarget,
        simIK.constraint_pose          -- full 6-DOF
    )

    print('[UR5 IK] IK environment initialized.')
end


function sysCall_actuation()
    -- Solve IK every simulation step
    local result = simIK.handleGroup(ikEnv, ikGroup, {syncWorlds=true, allowError=true})
    if result ~= simIK.result_success then
        -- Not an error if temporarily unreachable; just skip this step
    end
end


function sysCall_cleanup()
    if ikEnv then
        simIK.eraseEnvironment(ikEnv)
    end
end
