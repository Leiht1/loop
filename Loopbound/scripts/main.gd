extends Node3D

const PlayerController = preload("res://scripts/player/player_controller.gd")
const CameraController = preload("res://scripts/camera/camera_controller.gd")
const AnimationDriver = preload("res://scripts/animation/animation_driver.gd")
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
	var mesh := MeshInstance3D.new()
	mesh.name = "Placeholder"
	var capsule := CapsuleMesh.new()
	capsule.radius = 0.35
	capsule.height = 1.8
	mesh.mesh = capsule
	mesh.position.y = 0.9
	var material := StandardMaterial3D.new()
	material.albedo_color = Color("e2ae52")
	mesh.material_override = material
	socket.add_child(mesh)
	var nose := MeshInstance3D.new()
	var nose_mesh := BoxMesh.new()
	nose_mesh.size = Vector3(0.2, 0.15, 0.25)
	nose.mesh = nose_mesh
	nose.position = Vector3(0, 1.45, -0.35)
	socket.add_child(nose)
	var driver := Node.new()
	driver.set_script(AnimationDriver)
	driver.name = "AnimationDriver"
	player.add_child(driver)
	player.visual = visual
	player.animation_driver = driver
	add_child(player)

func build_camera() -> void:
	camera_rig = Node3D.new()
	camera_rig.set_script(CameraController)
	camera_rig.name = "CameraRig"
	camera_rig.target = player
	var pitch := Node3D.new()
	pitch.rotation.x = deg_to_rad(-15)
	camera_rig.add_child(pitch)
	var arm := SpringArm3D.new()
	arm.spring_length = 5
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
