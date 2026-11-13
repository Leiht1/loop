extends Node3D
@export var comparison_variants: Array[String] = ["triangles", "topology"]
@export var preview_subdir: String = "actions"
@export var synchronize_cycles: bool = false
@export var actions: Array[String] = ["idle", "walk", "run", "arms_overhead", "elbow_bend", "deep_squat"]
@export var one_shot_actions: Array[String] = []
@export var one_shot_displacements: Dictionary[String, Vector3] = {}
@export var use_function_view_keys: bool = false
@export var capture_phases: Array[float] = [0.0, 0.25, 0.5, 0.75, 0.999]
@export var help_text: String = "1 Idle   2 Walk   3 Run   4 Arms overhead   5 Elbow bend   6 Deep squat | 7 Front / 8 Side / 9 Back | Space Pause | G Gray / T Original"
var camera: Camera3D
var models: Array[Node3D] = []
var players: Array[AnimationPlayer] = []
var action_label: Label
func _ready() -> void:
	var env := WorldEnvironment.new()
	var settings := Environment.new()
	settings.background_mode = Environment.BG_COLOR
	settings.background_color = Color(0.12, 0.15, 0.2)
	settings.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	settings.ambient_light_energy = 0.55
	settings.ambient_light_color = Color(0.6, 0.65, 0.75)
	env.environment = settings
	add_child(env)
	var light := DirectionalLight3D.new()
	light.rotation_degrees = Vector3(-40, 150, 0)
	add_child(light)
	var fill := DirectionalLight3D.new()
	fill.rotation_degrees = Vector3(-30, -30, 0)
	fill.light_energy = 0.45
	add_child(fill)
	var floor_mesh := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(6, 6)
	floor_mesh.mesh = plane
	var floor_material := StandardMaterial3D.new()
	floor_material.albedo_color = Color(0.22, 0.25, 0.29)
	floor_mesh.material_override = floor_material
	floor_mesh.position.y = -0.005
	add_child(floor_mesh)
	camera = Camera3D.new()
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.size = 4.2
	camera.position = Vector3(0, 1.2, -4.0)
	add_child(camera)
	camera.look_at(Vector3(0, 0.9, 0))
	for index in comparison_variants.size():
		var variant := comparison_variants[index]
		var model = load("res://assets/characters/ranger/action_comparison/" + variant + ".glb").instantiate()
		model.position.x = (index - (comparison_variants.size() - 1) / 2.0) * 1.3
		add_child(model)
		models.append(model)
		for mesh in model.find_children("*", "MeshInstance3D", true, false):
			var material := StandardMaterial3D.new()
			material.albedo_color = Color(0.55, 0.57, 0.6)
			material.roughness = 0.85
			mesh.material_override = material
		for node in model.find_children("*", "AnimationPlayer", true, false):
			players.append(node)
		var label := Label3D.new()
		label.text = "LOCOMOTION V3 - 71 bones"
		label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		if synchronize_cycles:
			label.font_size = 20
		label.position = Vector3(model.position.x, 2.1, 0)
		add_child(label)
	var help := Label.new()
	help.text = help_text
	add_child(help)
	action_label = Label.new()
	action_label.position = Vector2(12, 30)
	add_child(action_label)
	if not one_shot_actions.is_empty():
		players[0].animation_finished.connect(_on_animation_finished)
	play_action("idle")
	if "--comparison-capture" in OS.get_cmdline_user_args():
		var preview_dir := ProjectSettings.globalize_path("res://").path_join("../local_previews/" + preview_subdir).simplify_path()
		DirAccess.make_dir_recursive_absolute(preview_dir)
		var views := {"front": 0.0, "side": PI / 2.0, "back": PI}
		for view in views:
			for model in models:
				model.rotation.y = views[view]
			for action in actions:
				for phase in capture_phases:
					for player in players:
						player.play(action, 0.0)
						player.advance(0.0)
						player.seek(player.current_animation_length * phase, true)
						player.pause()
					action_label.text = action
					await get_tree().process_frame
					await RenderingServer.frame_post_draw
					var file := "%s_%s_%03d.png" % [view, action, int(phase * 100)]
					var error := get_viewport().get_texture().get_image().save_png(preview_dir.path_join(file))
					assert(error == OK, "Capture failed")
		get_tree().quit()
	if "--comparison-smoke" in OS.get_cmdline_user_args():
		assert(players.size() == comparison_variants.size(), "Unexpected character animation player count")
		for action in actions:
			play_action(action)
			var duration := 0.0
			for player in players:
				duration = maxf(duration, player.get_animation(action).length)
			await get_tree().create_timer(duration + 0.2).timeout
			if action in one_shot_actions:
				assert(players[0].current_animation == "idle", "One-shot must return to idle")
		print("ACTION TEST PASS: ", players.size(), " players, ", actions.size(), " actions")
		get_tree().quit()
func play_action(action: String, blend: float = 0.15) -> void:
	action_label.text = action
	if action != "idle" and not one_shot_displacements.is_empty():
		for index in models.size():
			models[index].position = Vector3((index - (models.size() - 1) / 2.0) * 1.3, 0, 0)
	for player in players:
		assert(player.has_animation(action), "Missing action " + action)
		player.get_animation(action).loop_mode = Animation.LOOP_NONE if action in one_shot_actions else Animation.LOOP_LINEAR
		player.speed_scale = player.get_animation(action).length / players[-1].get_animation(action).length if synchronize_cycles else 1.0
		player.play(action, blend)
func _on_animation_finished(action: StringName) -> void:
	if "--comparison-capture" in OS.get_cmdline_user_args():
		return
	if action in one_shot_actions:
		if one_shot_displacements.has(action):
			for model in models:
				model.position += model.basis * one_shot_displacements[action]
			play_action("idle", 0.0)
			for player in players:
				player.advance(0.0)
		else:
			play_action("idle")
func _unhandled_key_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		var index: int = event.keycode - KEY_1
		if index >= 0 and index < actions.size():
			play_action(actions[index])
		if event.keycode in [KEY_G, KEY_T]:
			for mesh in find_children("*", "MeshInstance3D", true, false):
				var gray := StandardMaterial3D.new()
				gray.albedo_color = Color(0.65, 0.65, 0.65)
				mesh.material_override = gray if event.keycode == KEY_G else null


		var view_keys := [KEY_F1, KEY_F2, KEY_F3] if use_function_view_keys else [KEY_7, KEY_8, KEY_9]
		if event.keycode in view_keys:
			var angles := {view_keys[0]: 0.0, view_keys[1]: PI / 2.0, view_keys[2]: PI}
			for model in models:
				model.rotation.y = angles[event.keycode]
		if event.keycode == KEY_SPACE:
			for player in players:
				if player.is_playing():
					player.pause()
				else:
					player.play()
