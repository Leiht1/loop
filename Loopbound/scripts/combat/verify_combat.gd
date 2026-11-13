extends SceneTree
var failures := 0
func check(value: bool, message: String) -> void:
	print(("PASS " if value else "FAIL ") + message)
	if not value:
		failures += 1
func _initialize() -> void:
	call_deferred("run")
func frames(count: int) -> void:
	for frame in range(count):
		await physics_frame
func run() -> void:
	var arena: Node = load("res://scenes/test/combat_test_arena.tscn").instantiate()
	root.add_child(arena)
	await frames(10)
	var player: CharacterBody3D = arena.player
	var combat: Node = player.get_node("Combat")
	var weapon: Node3D = combat.weapon
	check(player.is_on_floor(), "spawn on floor")
	check(combat.skeleton.get_bone_count() == 71, "71 bone rig retained")
	check(InputMap.action_get_events("attack").size() == 2, "mouse and J mapped")
	combat.begin()
	var id: int = weapon.attack_id
	combat.begin()
	check(weapon.attack_id == id, "repeated attack rejected")
	await frames(20)
	check(weapon.active, "active window opens")
	combat.finish()
	check(not weapon.active and not weapon.attacking, "cancel disables damage immediately")
	await frames(10)
	var dummy: Node3D = arena.get_node("TrainingDummy")
	# Position the target at an actual blade sample to exercise the shared query.
	combat.begin()
	await frames(17)
	dummy.global_position = weapon.to_global(Vector3(0,0.55,0)) - Vector3(0,0.85,0)
	await frames(2)
	check(dummy.health == 75, "blade deals one hit")
	await frames(5)
	check(dummy.health == 75, "same swing deduplicates target")
	await frames(50)
	check(not weapon.active and not weapon.attacking, "recovery closes hit window")
	for direction in [Vector3.FORWARD, Vector3.BACK, Vector3.LEFT, Vector3.RIGHT]:
		player.start_dodge(direction)
		await frames(52)
		check(not player.dodging, "directional dodge completes")
	Input.action_press("move_forward")
	var start := player.position
	await frames(30)
	Input.action_release("move_forward")
	check(player.position.distance_to(start) > 0.5, "movement restored")
	print("COMBAT_FAILURES=", failures)
	quit(1 if failures else 0)

