extends SceneTree

## Headless test runner for SimulationCore.
## We bypass TimeManager and EventBus since autoload singletons
## aren't accessible by name in --script mode. We drive ticks manually.

func _initialize() -> void:
	print("--- PIZZATORIO V2 HEADLESS TEST ---")

	# Manually set up GlobalConfig as a named node on root
	# SimulationCore references it via the GlobalConfig class_name
	var GlobalConfigScript = load("res://src/autoloads/GlobalConfig.gd")
	var gc = GlobalConfigScript.new()
	gc.name = "GlobalConfig"
	root.add_child(gc)

	# Now load SimulationCore (it uses preload for catalogs internally)
	var SimCore = load("res://src/game/SimulationCore.gd")
	if SimCore == null:
		print("FAILED: Could not load SimulationCore.gd")
		quit(1)
		return

	var sim = SimCore.new()
	sim.name = "SimulationCore"
	root.add_child(sim)

	# Wait a frame for _ready() to fire
	await process_frame
	
	# Run assertions
	print("Grid size: %d x %d" % [sim.grid.size(), sim.grid[0].size()])
	print("Starting money: $%d" % sim.money)
	print("Reputation: %.1f" % sim.reputation)
	print("Tech tree entries: %d" % sim.tech_tree.size())
	
	# Verify static world placement
	var source_tile = sim.grid[7][1]
	print("Source tile at (1,7): %s" % source_tile["kind"])
	assert(source_tile["kind"] == "source", "Source tile should be at (1,7)")
	
	var sink_tile = sim.grid[7][18]
	print("Sink tile at (18,7): %s" % sink_tile["kind"])
	assert(sink_tile["kind"] == "sink", "Sink tile should be at (18,7)")
	
	var conveyor_tile = sim.grid[7][5]
	print("Conveyor tile at (5,7): %s" % conveyor_tile["kind"])
	assert(conveyor_tile["kind"] == "conveyor", "Conveyor should be at (5,7)")
	
	var processor_tile = sim.grid[7][7]
	print("Processor tile at (7,7): %s" % processor_tile["kind"])
	assert(processor_tile["kind"] == "processor", "Processor should be at (7,7)")
	
	# Test placing a tile
	var placed = sim.place_tile(5, 5, "conveyor", 0)
	print("Place conveyor at (5,5): %s" % str(placed))
	assert(placed == true, "Should be able to place conveyor at (5,5)")
	print("Money after placement: $%d" % sim.money)
	
	# Run a few simulation ticks manually
	for tick in range(10):
		sim.sim_tick(tick)
	print("Simulation ran 10 ticks. Time: %.1f" % sim.sim_time)
	print("Items on belt: %d" % sim.items.size())
	print("Orders: %d" % sim.orders.size())
	
	# Test serialization
	var save_data = sim.to_dict()
	assert(save_data.has("grid"), "Save data should contain grid")
	assert(save_data.has("money"), "Save data should contain money")
	print("Serialization OK: %d keys in save data" % save_data.size())
	
	print("\n--- ALL TESTS PASSED ---")
	quit(0)
