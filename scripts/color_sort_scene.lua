-- ============================================================
--  color_sort_scene.lua
--  CoppeliaSim Child Script — attach to the scene root or
--  to an empty "SceneManager" dummy object.
--
--  Responsibilities:
--    1. Spawn colored blocks on the conveyor at timed intervals
--    2. Drive the conveyor belt motor
--    3. Stop the conveyor when a block reaches the pickup sensor
--    4. Resume conveyor after the Python controller picks the block
-- ============================================================

-- ── Configuration ─────────────────────────────────────────────
local SPAWN_INTERVAL  = 4.0      -- seconds between block spawns
local CONVEYOR_SPEED  = 0.08     -- m/s
local BLOCK_SIZE      = 0.05     -- cube side length (m)
local BLOCK_MASS      = 0.2      -- kg
local PICKUP_WAIT     = 6.0      -- seconds to hold conveyor after detection

local COLORS = {
    {name='red',    rgb={1.0, 0.0, 0.0}},
    {name='green',  rgb={0.0, 0.8, 0.0}},
    {name='blue',   rgb={0.0, 0.3, 1.0}},
    {name='yellow', rgb={1.0, 0.85, 0.0}},
}

-- Scene object names — must match your scene hierarchy exactly
local CONVEYOR_JOINT  = '/ConveyorBelt'
local PROX_SENSOR     = '/ProxSensor'
local SPAWN_POINT     = '/SpawnPoint'     -- dummy marking spawn location
-- ──────────────────────────────────────────────────────────────

local conveyorHandle  = nil
local proxHandle      = nil
local spawnHandle     = nil
local lastSpawnTime   = -999
local conveyorStopped = false
local stopTimer       = 0
local blocks          = {}    -- list of spawned block handles


function sysCall_init()
    -- Get handles
    conveyorHandle = sim.getObject(CONVEYOR_JOINT)
    proxHandle     = sim.getObject(PROX_SENSOR)
    spawnHandle    = sim.getObject(SPAWN_POINT)

    -- Start conveyor
    sim.setJointTargetVelocity(conveyorHandle, CONVEYOR_SPEED)

    print('[Scene] Color Sorting Scene initialized.')
    print('[Scene] Conveyor running at ' .. CONVEYOR_SPEED .. ' m/s')
end


function spawnBlock()
    -- Pick a random color
    local c = COLORS[math.random(#COLORS)]

    -- Create a dynamic cube
    local handle = sim.createPureShape(
        0,          -- shape type: 0 = cuboid
        8+16+32,    -- options: respondable + dynamic + visible
        {BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE},
        BLOCK_MASS,
        nil
    )

    -- Apply color (ambient/diffuse)
    sim.setShapeColor(handle, nil, sim.colorcomponent_ambient_diffuse, c.rgb)
    sim.setShapeColor(handle, nil, sim.colorcomponent_emission,        {0.05, 0.05, 0.05})

    -- Position at spawn point
    local spawnPos = sim.getObjectPosition(spawnHandle, sim.handle_world)
    spawnPos[3] = spawnPos[3] + BLOCK_SIZE / 2 + 0.01   -- sit on conveyor
    sim.setObjectPosition(handle, sim.handle_world, spawnPos)

    -- Store color tag as custom data so Python can read it
    sim.writeCustomStringData(handle, 'blockColor', c.name)

    -- Name it for easy identification
    sim.setObjectAlias(handle, 'Block_' .. c.name .. '_' .. handle)

    table.insert(blocks, handle)
    print('[Scene] Spawned ' .. c.name .. ' block (handle=' .. handle .. ')')
    return handle
end


function sysCall_actuation()
    local t = sim.getSimulationTime()

    -- ── Spawn a block periodically ────────────────────────────────────────
    if (t - lastSpawnTime) >= SPAWN_INTERVAL then
        spawnBlock()
        lastSpawnTime = t
    end

    -- ── Proximity sensor: stop conveyor when block arrives ────────────────
    if not conveyorStopped then
        local result, dist, point, objHandle = sim.readProximitySensor(proxHandle)
        if result == 1 then
            sim.setJointTargetVelocity(conveyorHandle, 0)
            conveyorStopped = true
            stopTimer       = t
            print('[Scene] Block detected at pickup zone — conveyor stopped.')
        end
    else
        -- Resume conveyor after PICKUP_WAIT (in case Python already picked the block)
        if (t - stopTimer) >= PICKUP_WAIT then
            sim.setJointTargetVelocity(conveyorHandle, CONVEYOR_SPEED)
            conveyorStopped = false
            print('[Scene] Resuming conveyor.')
        end
    end

    -- ── Clean up blocks that have fallen off ─────────────────────────────
    for i = #blocks, 1, -1 do
        local h = blocks[i]
        local ok, pos = pcall(sim.getObjectPosition, h, sim.handle_world)
        if not ok or pos[3] < -0.5 then
            pcall(sim.removeObject, h)
            table.remove(blocks, i)
        end
    end
end


function sysCall_cleanup()
    -- Remove all spawned blocks on simulation stop
    for _, h in ipairs(blocks) do
        pcall(sim.removeObject, h)
    end
    blocks = {}
    print('[Scene] Cleanup complete.')
end
