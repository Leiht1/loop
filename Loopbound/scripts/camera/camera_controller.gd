extends Node3D

@export var sensitivity := 0.0025
@export var distance := 5.0
@export var follow_speed := 18.0
@export var min_pitch := -65.0
@export var max_pitch := 35.0
var target: Node3D
var pitch: Node3D
var arm: SpringArm3D

func _ready() -> void:
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	global_position = target.global_position + Vector3.UP * 1.25

func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("ui_cancel"):
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE if Input.mouse_mode == Input.MOUSE_MODE_CAPTURED else Input.MOUSE_MODE_CAPTURED
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		rotation.y -= event.relative.x * sensitivity
		pitch.rotation.x = clampf(pitch.rotation.x - event.relative.y * sensitivity, deg_to_rad(min_pitch), deg_to_rad(max_pitch))

func _physics_process(delta: float) -> void:
	global_position = global_position.lerp(target.global_position + Vector3.UP * 1.25, 1.0 - exp(-follow_speed * delta))
	arm.spring_length = distance
