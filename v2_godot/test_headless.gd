extends SceneTree

## Headless test runner for SimulationCore and LocationManager.
## We bypass TimeManager and EventBus since autoload singletons
## aren't accessible by name in --script mode. We drive ticks manually.

func _initialize() -> void:
	print("--- PIZZATORIO V2 HEADLESS TEST ---")

	# Manually set up GlobalConfig as a named node on root
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
	assert(save_data.has("location_key"), "Save data should contain location_key")
	assert(save_data.has("grid_w"), "Save data should contain grid_w")
	assert(save_data.has("grid_h"), "Save data should contain grid_h")
	print("Serialization OK: %d keys in save data" % save_data.size())

	# Test instance grid dimensions
	assert(sim.grid_w == 20, "Default grid_w should be 20")
	assert(sim.grid_h == 15, "Default grid_h should be 15")
	print("Instance grid dimensions: %d x %d" % [sim.grid_w, sim.grid_h])

	print("\n--- SIMULATIONCORE TESTS PASSED ---")

	# ---------------------------------------------------------------
	# LocationManager tests
	# ---------------------------------------------------------------
	print("\n--- LOCATIONMANAGER TESTS ---")

	var LocMgr = load("res://src/game/LocationManager.gd")
	if LocMgr == null:
		print("FAILED: Could not load LocationManager.gd")
		quit(1)
		return

	var loc_mgr = LocMgr.new()
	loc_mgr.name = "LocationManager"
	root.add_child(loc_mgr)

	await process_frame

	# Test: add first location (pizza_shop)
	var added = loc_mgr.add_location("pizza_shop_1", "pizza_shop", "Main Pizza Shop")
	assert(added == true, "Should be able to add pizza_shop location")
	print("Added pizza_shop_1: %s" % str(added))

	assert(loc_mgr.get_location_count() == 1, "Should have 1 location")
	assert(loc_mgr.active_location == "pizza_shop_1", "Active location should be pizza_shop_1")
	print("Active location: %s" % loc_mgr.active_location)

	# Test: get active simulation
	var active_sim = loc_mgr.get_active_simulation()
	assert(active_sim != null, "Active simulation should not be null")
	assert(active_sim.location_key == "pizza_shop_1", "Sim location_key should match")
	assert(active_sim.grid_w == 20, "Pizza shop grid_w should be 20")
	assert(active_sim.grid_h == 15, "Pizza shop grid_h should be 15")
	print("Active sim grid: %d x %d" % [active_sim.grid_w, active_sim.grid_h])

	# Verify pizza shop has standard layout
	assert(active_sim.grid[7][1]["kind"] == "source", "Pizza shop should have source at (1,7)")
	assert(active_sim.grid[7][18]["kind"] == "sink", "Pizza shop should have sink at (18,7)")
	print("Pizza shop static world: OK")

	# Test: tick the location
	loc_mgr.tick_all(1)
	print("LocationManager tick_all: OK (sim_time=%.1f)" % active_sim.sim_time)

	# Test: add second location (dough_factory) — costs 500
	var money_before = loc_mgr.shared_money
	var added2 = loc_mgr.add_location("dough_factory_1", "dough_factory", "Dough Factory")
	assert(added2 == true, "Should be able to add dough_factory location")
	assert(loc_mgr.get_location_count() == 2, "Should have 2 locations")
	assert(loc_mgr.shared_money == money_before - 500, "Should charge 500 for dough factory")
	print("Added dough_factory_1 (cost 500). Money: %d -> %d" % [money_before, loc_mgr.shared_money])

	# Test: dough factory grid dimensions
	var dough_sim = loc_mgr.get_simulation("dough_factory_1")
	assert(dough_sim != null, "Dough factory simulation should exist")
	assert(dough_sim.grid_w == 16, "Dough factory grid_w should be 16")
	assert(dough_sim.grid_h == 12, "Dough factory grid_h should be 12")
	print("Dough factory grid: %d x %d" % [dough_sim.grid_w, dough_sim.grid_h])

	# Verify dough factory has non-pizza-shop layout (source at 0, sink at grid_w-1)
	var dough_mid_y = dough_sim.grid_h / 2
	assert(dough_sim.grid[dough_mid_y][0]["kind"] == "source", "Dough factory source at (0, mid)")
	assert(dough_sim.grid[dough_mid_y][dough_sim.grid_w - 1]["kind"] == "sink", "Dough factory sink at (grid_w-1, mid)")
	print("Dough factory static world: OK")

	# Test: switch location
	var switched = loc_mgr.switch_location("dough_factory_1")
	assert(switched == true, "Should switch to dough_factory_1")
	assert(loc_mgr.active_location == "dough_factory_1", "Active should be dough_factory_1")
	print("Switched to: %s" % loc_mgr.active_location)

	# Test: cycle next
	loc_mgr.switch_to_next_location()
	assert(loc_mgr.active_location == "pizza_shop_1", "Should cycle back to pizza_shop_1")
	print("Cycled to next: %s" % loc_mgr.active_location)

	# Test: add transport link
	var link_added = loc_mgr.add_transport_link("dough_factory_1", "pizza_shop_1", ["rolled_pizza_base"], 5.0)
	assert(link_added == true, "Should add transport link")
	assert(loc_mgr.transport_links.size() == 1, "Should have 1 transport link")
	print("Transport link added: dough_factory -> pizza_shop")

	# Test: tick all locations (both should advance)
	var ps_time_before = active_sim.sim_time
	var df_time_before = dough_sim.sim_time
	loc_mgr.tick_all(2)
	assert(active_sim.sim_time > ps_time_before, "Pizza shop sim_time should advance")
	assert(dough_sim.sim_time > df_time_before, "Dough factory sim_time should advance")
	print("Both locations ticked independently: OK")

	# Test: serialization
	var loc_save = loc_mgr.to_dict()
	assert(loc_save.has("locations"), "Save should have locations")
	assert(loc_save.has("transport_links"), "Save should have transport_links")
	assert(loc_save.has("active_location"), "Save should have active_location")
	assert(loc_save.has("shared_money"), "Save should have shared_money")
	assert(loc_save["locations"].size() == 2, "Save should have 2 locations")
	assert(loc_save["transport_links"].size() == 1, "Save should have 1 transport link")
	print("LocationManager serialization: OK (%d keys)" % loc_save.size())

	# Test: load from dict (round-trip)
	var loc_mgr2 = LocMgr.new()
	loc_mgr2.name = "LocationManager2"
	root.add_child(loc_mgr2)
	await process_frame
	loc_mgr2.load_from_dict(loc_save)
	assert(loc_mgr2.get_location_count() == 2, "Loaded manager should have 2 locations")
	assert(loc_mgr2.active_location == "pizza_shop_1", "Loaded active should be pizza_shop_1")
	assert(loc_mgr2.transport_links.size() == 1, "Loaded should have 1 transport link")
	var loaded_sim = loc_mgr2.get_active_simulation()
	assert(loaded_sim != null, "Loaded active sim should exist")
	assert(loaded_sim.grid_w == 20, "Loaded pizza shop grid_w should be 20")
	print("LocationManager load_from_dict round-trip: OK")

	# Test: LOCATION_TYPES config
	var GCScript = load("res://src/autoloads/GlobalConfig.gd")
	assert(GCScript.LOCATION_TYPES.has("pizza_shop"), "Should have pizza_shop type")
	assert(GCScript.LOCATION_TYPES.has("dough_factory"), "Should have dough_factory type")
	assert(GCScript.LOCATION_TYPES.has("sauce_plant"), "Should have sauce_plant type")
	assert(GCScript.LOCATION_TYPES.has("farm"), "Should have farm type")
	print("LOCATION_TYPES config: %d types defined" % GCScript.LOCATION_TYPES.size())

	# Test: cannot add duplicate location key
	var dup_added = loc_mgr.add_location("pizza_shop_1", "pizza_shop")
	assert(dup_added == false, "Should not add duplicate location key")
	print("Duplicate key rejected: OK")

	# Test: cannot remove last location
	# First remove dough factory, then try to remove pizza shop
	loc_mgr.switch_location("pizza_shop_1")
	loc_mgr.remove_location("dough_factory_1")
	assert(loc_mgr.get_location_count() == 1, "Should have 1 location after removal")
	var removed_last = loc_mgr.remove_location("pizza_shop_1")
	assert(removed_last == false, "Should not remove last location")
	print("Cannot remove last location: OK")

	print("\n--- ALL TESTS PASSED ---")
	quit(0)
