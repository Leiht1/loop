extends CharacterBody3D

@export var walk_speed := 2.6
@export var run_speed := 6.0
@export var acceleration := 18.0
@export var deceleration := 22.0
@export var turn_speed := 12.0
var camera_rig: Node3D
var visual: Node3D
var animation_driver: Node

func _physics_process(delta: float) -> void:
	var input := Input.get_vector("move_left", "move_right", "move_forward", "move_backward")
	var direction := Vector3(input.x, 0, input.y).rotated(Vector3.UP, camera_rig.rotation.y)
	var speed := run_speed if Input.is_action_pressed("sprint") else walk_speed
	var rate := acceleration if direction.length_squared() > 0 else deceleration
	velocity.x = move_toward(velocity.x, direction.x * speed, rate * delta)
	velocity.z = move_toward(velocity.z, direction.z * speed, rate * delta)
	if not is_on_floor():
		velocity.y -= 9.8 * delta
	move_and_slide()
	var horizontal := Vector2(velocity.x, velocity.z).length()
	if horizontal > 0.05:
		visual.rotation.y = lerp_angle(visual.rotation.y, atan2(-velocity.x, -velocity.z), 1.0 - exp(-turn_speed * delta))
	animation_driver.update_motion(horizontal, delta)
