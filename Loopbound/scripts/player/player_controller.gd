extends CharacterBody3D

@export var walk_speed := 2.0
@export var run_speed := 4.0
@export var acceleration := 18.0
@export var deceleration := 22.0
@export var turn_speed := 12.0
@export var dodge_forward_distance := 3.3
@export var dodge_backward_distance := 2.8
@export var dodge_side_distance := 3.0
var dodge_distance := 1.6
var dodge_entry_velocity := Vector3.ZERO
const DODGE_DURATION := 0.8
var dodge_elapsed := 0.0
var dodging := false
var dodge_direction := Vector3.ZERO
var turn_detector = preload("res://scripts/animation/turn_threshold.gd").new()
var turn_elapsed := 0.0
var turn_duration := 0.0
var turn_start_yaw := 0.0
var turn_target_yaw := 0.0
var turn_quiet := 0.0
var turn_input_elapsed := 0.0
var turn_angle := 0.0
var last_camera_yaw := 0.0
var camera_rig: Node3D
var visual: Node3D
var animation_driver: Node

func combat_locked() -> bool:
	var combat := get_node_or_null("Combat")
	return combat != null and combat.weapon != null and combat.weapon.attacking


func _physics_process(delta: float) -> void:
	var input := Input.get_vector("move_left", "move_right", "move_forward", "move_backward")
	var direction := Vector3(input.x, 0, input.y).rotated(Vector3.UP, camera_rig.rotation.y)
	update_facing(delta, input.length())
	if Input.is_action_just_pressed("dodge") and not dodging and is_on_floor():
		if combat_locked():
			var combat := get_node("Combat")
			if combat.weapon.elapsed >= combat.dodge_cancel_time:
				combat.finish()
				start_dodge(direction)
		else:
			start_dodge(direction)
	if dodging:
		update_dodge(delta, direction)
		return
	if combat_locked():
		var combat := get_node("Combat")
		var phase: float = combat.weapon.elapsed
		var drive := 0.0 # Attack_01 is an in-place cut.
		var forward := -visual.global_basis.z
		velocity.x = move_toward(velocity.x, forward.x * drive, deceleration * delta)
		velocity.z = move_toward(velocity.z, forward.z * drive, deceleration * delta)
		animation_driver.update_motion(0.0, delta)
		if not is_on_floor():
			velocity.y -= 9.8 * delta
		move_and_slide()
		return
	var speed := movement_speed(input)
	var rate := acceleration if direction.length_squared() > 0 else deceleration
	velocity.x = move_toward(velocity.x, direction.x * speed, rate * delta)
	velocity.z = move_toward(velocity.z, direction.z * speed, rate * delta)
	if not is_on_floor():
		velocity.y -= 9.8 * delta
	move_and_slide()
	var horizontal := Vector2(velocity.x, velocity.z).length()
	var local_velocity := Vector3(velocity.x, 0, velocity.z).rotated(Vector3.UP, -visual.rotation.y)
	animation_driver.motion_direction = Vector2(local_velocity.x, -local_velocity.z)
	animation_driver.fast_strafe = Input.is_action_pressed("sprint") and input.y >= -0.1
	animation_driver.update_motion(horizontal, delta)

func update_facing(delta: float, moving: float) -> void:
	var camera_yaw := camera_rig.rotation.y
	var changed := absf(angle_difference(last_camera_yaw, camera_yaw)) > 0.0001
	last_camera_yaw = camera_yaw
	turn_quiet = 0.0 if changed else turn_quiet + delta
	turn_input_elapsed += delta
	if turn_quiet >= 0.12:
		turn_input_elapsed = 0.0
	var busy := dodging or combat_locked()
	var event: int = turn_detector.sample_yaw(camera_yaw, delta, moving > 0.1, busy or turn_duration > 0.0)
	if turn_duration > 0.0:
		turn_elapsed += delta
		var progress := smoothstep(0.0, turn_duration, turn_elapsed)
		visual.rotation.y = lerp_angle(turn_start_yaw, turn_target_yaw - turn_angle, progress)
		if busy or moving > 0.1 or turn_elapsed >= turn_duration:
			visual.rotation.y = turn_target_yaw
			turn_duration = 0.0
			animation_driver.cancel_turn()
		return
	if busy:
		return
	if event != 0:
		turn_start_yaw = visual.rotation.y
		turn_angle = deg_to_rad(float(event))
		turn_target_yaw = camera_yaw
		turn_elapsed = 0.0
		turn_duration = animation_driver.play_turn(event)
	elif moving > 0.1 or turn_quiet >= 0.12 or turn_input_elapsed >= 0.5:
		visual.rotation.y = lerp_angle(visual.rotation.y, camera_yaw, 1.0 - exp(-turn_speed * delta))

func movement_speed(input: Vector2) -> float:
	if not Input.is_action_pressed("sprint"):
		return walk_speed
	return run_speed if input.y < -0.1 else walk_speed * 1.5

func start_dodge(direction: Vector3) -> void:
	var forward := -visual.global_basis.z
	dodge_direction = direction.normalized() if direction.length_squared() > 0.01 else forward
	var local_direction := visual.global_basis.inverse() * dodge_direction
	var clip := "front"
	if absf(local_direction.x) > absf(local_direction.z):
		clip = "right" if local_direction.x > 0.0 else "left"
	elif local_direction.z > 0.0:
		clip = "back"
	dodge_distance = dodge_side_distance if clip in ["left", "right"] else (dodge_backward_distance if clip == "back" else dodge_forward_distance)
	dodge_entry_velocity = Vector3(velocity.x, 0, velocity.z)
	dodge_elapsed = 0.0
	dodging = true
	animation_driver.play_dodge(clip)

func dodge_progress(phase: float) -> float:
	# Cubic Hermite segments match the baked push-off, glide and landing phases.
	var times := [0.0, 0.12, 0.22, 0.64, 0.84, 1.0]
	var positions := [0.0, 0.0, 0.12, 0.86, 1.0, 1.0]
	var slopes := [0.0, 0.0, 1.8, 1.7, 0.0, 0.0]
	for index in range(times.size() - 1):
		if phase <= times[index + 1]:
			var width: float = times[index + 1] - times[index]
			var t := clampf((phase - times[index]) / width, 0.0, 1.0)
			var start_weight := 2 * t * t * t - 3 * t * t + 1
			var start_tangent := t * t * t - 2 * t * t + t
			var end_weight := -2 * t * t * t + 3 * t * t
			var end_tangent := t * t * t - t * t
			return (start_weight * positions[index]
				+ start_tangent * width * slopes[index]
				+ end_weight * positions[index + 1]
				+ end_tangent * width * slopes[index + 1])
	return 1.0

func dodge_offset(phase: float) -> Vector3:
	var progress := dodge_progress(phase)
	var t := clampf(phase / 0.18, 0.0, 1.0)
	# Integrate the incoming velocity while fading it out, then compensate its travel.
	var carry := t - t * t * t + 0.5 * t * t * t * t - 0.5 * progress
	return dodge_direction * dodge_distance * progress + dodge_entry_velocity * DODGE_DURATION * 0.18 * carry

func update_dodge(delta: float, direction: Vector3) -> void:
	var previous := dodge_offset(dodge_elapsed / DODGE_DURATION)
	dodge_elapsed = minf(dodge_elapsed + delta, DODGE_DURATION)
	var travel := dodge_offset(dodge_elapsed / DODGE_DURATION) - previous
	velocity.x = travel.x / delta
	velocity.z = travel.z / delta
	if not is_on_floor():
		velocity.y -= 9.8 * delta
	move_and_slide()
	var locomotion_speed := movement_speed(Input.get_vector("move_left", "move_right", "move_forward", "move_backward")) * direction.length()
	var local_motion := direction.rotated(Vector3.UP, -visual.rotation.y) * locomotion_speed
	animation_driver.motion_direction = Vector2(local_motion.x, -local_motion.z)
	animation_driver.update_motion(locomotion_speed, delta)
	if dodge_elapsed >= DODGE_DURATION:
		dodging = false
		velocity.x = direction.normalized().x * locomotion_speed
		velocity.z = direction.normalized().z * locomotion_speed
