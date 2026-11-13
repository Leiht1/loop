extends Node3D

const PlayerController = preload("res://scripts/player/player_controller.gd")
const CameraController = preload("res://scripts/camera/camera_controller.gd")
const AnimationDriver = preload("res://scripts/animation/animation_driver.gd")
const RangerModel = preload("res://assets/characters/ranger/action_comparison/locomotion_v3.glb")
var player: CharacterBody3D
var camera_rig: Node3D

func _ready() -> void:
	setup_input()
	build_arena()
	build_player()
	build_camera()

func setup_input() -> void:
	# Mouse motion uses InputEventMouseMotion because InputMap has no motion axis event.
	pass

func block(label: String, size: Vector3, location: Vector3, color: Color) -> void:
	var body := StaticBody3D.new()
	body.name = label
	body.position = location
	var mesh := MeshInstance3D.new()
	var box := BoxMesh.new()
	box.size = size
	mesh.mesh = box
	var material := StandardMaterial3D.new()
	material.albedo_color = color
	mesh.material_override = material
	var collision := CollisionShape3D.new()
	var shape := BoxShape3D.new()
	shape.size = size
	collision.shape = shape
	body.add_child(mesh)
	body.add_child(collision)
	add_child(body)

func build_arena() -> void:
	var environment := WorldEnvironment.new()
	var settings := Environment.new()
	settings.background_mode = Environment.BG_COLOR
	settings.background_color = Color("263746")
	settings.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	settings.ambient_light_color = Color("b9d4ed")
	settings.ambient_light_energy = 0.65
	environment.environment = settings
	add_child(environment)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-45, -35, 0)
	sun.light_energy = 1.5
	sun.shadow_enabled = true
	add_child(sun)
	block("Ground", Vector3(36, 1, 36), Vector3(0, -0.5, 0), Color("73858b"))
	for side in [-1, 1]:
		block("BoundaryX", Vector3(1, 2, 36), Vector3(side * 18, 1, 0), Color("485969"))
		block("BoundaryZ", Vector3(36, 2, 1), Vector3(0, 1, side * 18), Color("485969"))
		block("GatePillar", Vector3(1.3, 4, 1.3), Vector3(side * 3, 2, -8), Color("a5b5bb"))
		block("Ruins", Vector3(2, 2.5, 4), Vector3(side * 11, 1.25, -3), Color("8799a4"))
	block("GateLintel", Vector3(7.5, 0.7, 1.5), Vector3(0, 4.2, -8), Color("a5b5bb"))
	block("OrientationMarker", Vector3(3, 0.02, 1), Vector3(0, 0.02, -5), Color("d6b86c"))

func build_player() -> void:
	player = CharacterBody3D.new()
	player.set_script(PlayerController)
	player.name = "Player"
	player.position = Vector3(0, 0.1, 3)
	player.collision_layer = 2
	player.collision_mask = 1
	var collision := CollisionShape3D.new()
	var shape := CapsuleShape3D.new()
	shape.radius = 0.35
	shape.height = 1.8
	collision.shape = shape
	collision.position.y = 0.9
	player.add_child(collision)
	var visual := Node3D.new()
	visual.name = "Visual"
	player.add_child(visual)
	var socket := Node3D.new()
	socket.name = "ModelSocket"
	visual.add_child(socket)
	var model := RangerModel.instantiate() as Node3D
	socket.add_child(model)
	var driver := Node.new()
	driver.set_script(AnimationDriver)
	driver.name = "AnimationDriver"
	player.add_child(driver)
	player.visual = visual
	player.animation_driver = driver
	add_child(player)
	driver.animation_tree = build_ranger_animation_tree(model)
	driver.dodge_node = driver.animation_tree.tree_root.get_node("dodge")

func build_ranger_animation_tree(model: Node) -> AnimationTree:
	var clips := model.get_node_or_null("AnimationPlayer") as AnimationPlayer
	if clips == null:
		return null
	# Each gameplay instance owns its edited clips; the preview keeps baked root travel.
	for library_name in clips.get_animation_library_list():
		var library := clips.get_animation_library(library_name).duplicate(true) as AnimationLibrary
		clips.remove_animation_library(library_name)
		clips.add_animation_library(library_name, library)
	var replacements := {"idle":"Idle", "walk":"Walk", "run":"Run", "walk_left":"Left", "walk_right":"Right", "walk_back":"Back", "turn_left":"OriginalTurnLeft", "turn_right":"OriginalTurnRight"}
	var library := clips.get_animation_library("")
	for clip_name in replacements:
		var animation := load("res://assets/animations/Library_" + replacements[clip_name] + ".tres").duplicate(true) as Animation
		animation.loop_mode = Animation.LOOP_NONE if clip_name.begins_with("turn_") else Animation.LOOP_LINEAR
		if library.has_animation(clip_name):
			library.remove_animation(clip_name)
		library.add_animation(clip_name, animation)
	library.remove_animation("look_around")
	library.add_animation("look_around", clips.get_animation("idle").duplicate(true))
	var blend := AnimationNodeBlendSpace2D.new()
	blend.min_space = Vector2(-4, -4)
	blend.max_space = Vector2(4, 4)
	blend.sync = true
	var positions := {"idle":Vector2.ZERO, "walk":Vector2(0,2), "run":Vector2(0,4), "walk_left":Vector2(-2,0), "walk_right":Vector2(2,0), "walk_back":Vector2(0,-2)}
	for clip_name in positions:
		var node := AnimationNodeAnimation.new()
		node.animation = clip_name
		blend.add_blend_point(node, positions[clip_name], -1, clip_name)
	# Horizontal travel belongs to CharacterBody3D so walls constrain each dodge.
	for clip: String in ["dodge_front", "dodge_back", "dodge_left", "dodge_right"]:
		var animation := clips.get_animation(clip)
		animation.loop_mode = Animation.LOOP_NONE
		for track in animation.get_track_count():
			if animation.track_get_type(track) == Animation.TYPE_POSITION_3D and String(animation.track_get_path(track)).ends_with(":Root"):
				for key in animation.track_get_key_count(track):
					var position: Vector3 = animation.track_get_key_value(track, key)
					animation.track_set_key_value(track, key, Vector3(0, position.y, 0))
	var dodge := AnimationNodeAnimation.new()
	dodge.animation = "dodge_front"
	var one_shot := AnimationNodeOneShot.new()
	one_shot.sync = true
	one_shot.fadein_time = 0.09
	one_shot.fadeout_time = 0.12
	var graph := AnimationNodeBlendTree.new()
	graph.add_node("locomotion", blend, Vector2(0, 100))
	graph.add_node("motion_rate", AnimationNodeTimeScale.new())
	var turn_clip := AnimationNodeAnimation.new()
	turn_clip.animation = "turn_left"
	graph.add_node("turn_clip", turn_clip)
	var turn := AnimationNodeOneShot.new()
	turn.fadein_time = 0.04
	turn.fadeout_time = 0.0
	graph.add_node("turn", turn)
	graph.connect_node("motion_rate", 0, "locomotion")
	graph.connect_node("turn", 0, "motion_rate")
	graph.connect_node("turn", 1, "turn_clip")
	graph.add_node("dodge", dodge, Vector2(0, 300))
	graph.add_node("evasion", one_shot, Vector2(250, 100))
	clips.get_animation("look_around").loop_mode = Animation.LOOP_NONE
	var look := AnimationNodeAnimation.new()
	look.animation = "look_around"
	var idle_variation := AnimationNodeOneShot.new()
	idle_variation.sync = true
	idle_variation.fadein_time = 0.4
	idle_variation.fadeout_time = 0.2
	graph.add_node("look", look, Vector2(0, -200))
	graph.add_node("idle_variation", idle_variation, Vector2(150, 0))
	graph.connect_node("idle_variation", 0, "turn")
	graph.connect_node("idle_variation", 1, "look")
	graph.connect_node("evasion", 0, "idle_variation")
	graph.connect_node("evasion", 1, "dodge")
	graph.connect_node("output", 0, "evasion")
	var tree := AnimationTree.new()
	tree.name = "Locomotion"
	tree.tree_root = graph
	tree.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_PHYSICS
	model.add_child(tree)
	tree.anim_player = tree.get_path_to(clips)
	tree.root_node = tree.get_path_to(clips.get_node(clips.root_node))
	tree.active = true
	return tree

func build_camera() -> void:
	camera_rig = Node3D.new()
	camera_rig.set_script(CameraController)
	camera_rig.name = "CameraRig"
	camera_rig.target = player
	var pitch := Node3D.new()
	pitch.rotation.x = deg_to_rad(-15)
	camera_rig.add_child(pitch)
	var arm := SpringArm3D.new()
	arm.margin = 0.2
	arm.collision_mask = 1
	var shape := SphereShape3D.new()
	shape.radius = 0.25
	arm.shape = shape
	pitch.add_child(arm)
	var camera := Camera3D.new()
	camera.current = true
	camera.fov = 65
	camera.near = 0.1
	arm.add_child(camera)
	camera_rig.pitch = pitch
	camera_rig.arm = arm
	player.camera_rig = camera_rig
	add_child(camera_rig)
