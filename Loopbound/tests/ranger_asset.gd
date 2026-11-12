extends SceneTree

var failures := 0
var preview_dir := ""

func _initialize() -> void:
	call_deferred("run")

func check(condition: bool, label: String) -> void:
	print(("PASS " if condition else "FAIL ") + label)
	if not condition:
		failures += 1

func wait_frames(count: int) -> void:
	for i in count:
		await physics_frame

func scroll(button: MouseButton, steps: int) -> void:
	for i in steps:
		var event := InputEventMouseButton.new()
		event.button_index = button
		event.pressed = true
		Input.parse_input_event(event)
	Input.flush_buffered_events()

func capture(name: String) -> void:
	if DisplayServer.get_name() == "headless" or preview_dir.is_empty():
		return
	await RenderingServer.frame_post_draw
	check(root.get_texture().get_image().save_png(preview_dir.path_join(name + ".png")) == OK, name + " screenshot")

func run() -> void:
	var args := OS.get_cmdline_user_args()
	if not args.is_empty():
		preview_dir = args[0]
	var stage = load("res://scenes/main/main.tscn").instantiate()
	root.add_child(stage)
	await wait_frames(45)
	var player = stage.player
	var socket := player.get_node("Visual/ModelSocket") as Node3D
	var model := socket.get_child(0) as Node3D
	var meshes := model.find_children("*", "MeshInstance3D", true, false)
	check(meshes.size() == 1, "one imported character mesh")
	if meshes.size() != 1:
		quit(1)
		return
	var mesh := meshes[0] as MeshInstance3D
	var bounds := mesh.global_transform * mesh.get_aabb()
	check(mesh.mesh.get_surface_count() == 3, "base mesh and both repair surfaces imported")
	check(absf(bounds.size.y - 1.78) < 0.005, "character is 1.78 m tall")
	check(player.is_on_floor() and absf(bounds.position.y) < 0.025, "mesh soles rest at ground height")
	check(model.transform.basis.x.normalized().is_equal_approx(Vector3.FORWARD), "source front maps to -Z")
	check(player.animation_driver.animation_tree == null, "unrigged model loads without an animation tree")
	await capture("tripo_ingame")

	var camera = stage.camera_rig
	check(is_equal_approx(camera.arm.spring_length, 5.0), "camera starts at 5 m")
	scroll(MOUSE_BUTTON_WHEEL_UP, 24)
	await wait_frames(40)
	check(absf(camera.arm.spring_length - 1.15) < 0.01, "wheel up eases to near limit")
	camera.rotation.y = PI
	await wait_frames(5)
	await capture("tripo_zoom_near")
	camera.rotation.y = 0.0
	scroll(MOUSE_BUTTON_WHEEL_DOWN, 24)
	await wait_frames(40)
	check(absf(camera.arm.spring_length - 8.0) < 0.01, "wheel down eases to far limit")

	var start := model.global_position
	Input.action_press("move_forward")
	await wait_frames(38)
	check(model.global_position.z < start.z - 1.0, "model follows walking player")
	check(player.animation_driver.state == "walk", "walk state")
	Input.action_press("sprint")
	await wait_frames(38)
	check(player.animation_driver.state == "run", "run state")
	Input.action_release("move_forward")
	Input.action_release("sprint")
	await wait_frames(38)
	check(player.animation_driver.state == "idle", "idle state")
	print("FAILURES ", failures)
	quit(failures)
