extends SceneTree
var failures := 0
func check(value: bool, label: String) -> void:
	print(("PASS " if value else "FAIL ") + label)
	if not value:
		failures += 1
func wait_frames(count: int) -> void:
	for i in count:
		await physics_frame
func _initialize() -> void:
	call_deferred("run")
func run() -> void:
	var scene = load("res://scenes/main/main.tscn").instantiate()
	root.add_child(scene)
	await wait_frames(60)
	var p = scene.player
	check(p.is_on_floor(), "ground contact")
	var start: Vector3 = p.position
	Input.action_press("move_forward")
	await wait_frames(60)
	check(p.position.z < start.z - 2.0, "forward movement")
	check(p.animation_driver.state == "walk", "walk state")
	Input.action_press("sprint")
	await wait_frames(30)
	check(p.velocity.length() > 5.5, "run speed")
	check(p.animation_driver.state == "run", "run state")
	Input.action_release("move_forward")
	Input.action_release("sprint")
	await wait_frames(40)
	check(p.animation_driver.state == "idle", "idle state")
	p.position = Vector3(0, 0.05, 0)
	scene.camera_rig.rotation.y = PI / 2
	Input.action_press("move_forward")
	await wait_frames(60)
	check(p.position.x < -2.0, "camera relative movement")
	Input.action_release("move_forward")
	p.position = Vector3(16, 0.05, 8)
	scene.camera_rig.rotation.y = 0
	Input.action_press("move_right")
	await wait_frames(120)
	check(p.position.x < 17.3, "boundary collision")
	Input.action_release("move_right")
	p.position = Vector3(0, 0.05, 16)
	await wait_frames(90)
	check(scene.camera_rig.arm.get_hit_length() < 3.0, "camera wall contraction")
	scene.camera_rig.rotation.y = 0
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	var motion := InputEventMouseMotion.new()
	motion.relative = Vector2(100, 100000)
	scene.camera_rig._unhandled_input(motion)
	if DisplayServer.get_name() != "headless":
		check(absf(angle_difference(scene.camera_rig.rotation.y, -0.25)) < 0.001, "mouse yaw")
	else:
		print("SKIP mouse capture requires interactive display")
	check(scene.camera_rig.pitch.rotation.x >= deg_to_rad(-65.0), "pitch clamp")
	p.position = Vector3(0, 0.05, 3)
	scene.camera_rig.rotation.y = 0
	scene.camera_rig.pitch.rotation.x = deg_to_rad(-15)
	await wait_frames(60)
	await process_frame
	if DisplayServer.get_name() == "headless":
		print("FAILURES ", failures)
		quit(failures)
		return
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png("res://../docs/phase_1_preview.png")
	print("FAILURES ", failures)
	quit(failures)


