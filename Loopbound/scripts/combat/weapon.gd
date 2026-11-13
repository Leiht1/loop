extends Node3D
signal hit_confirmed(position: Vector3)
var combo_windows: Array[Vector2] = []
var combo_index := -1
var hit_pause := 0.0
signal attack_event(phase: String, attack_id: int)
@export var damage := 25.0
@export var duration := 0.85
@export var active_start := 0.24
@export var active_end := 0.48
@export var hit_radius := 0.12
var elapsed := 0.0
var attacking := false
var active := false
var attack_id := 0
var hit_targets := {}
var previous_transform := Transform3D.IDENTITY
var query_shape := CapsuleShape3D.new()
var query := PhysicsShapeQueryParameters3D.new()

func _ready() -> void:
	query_shape.radius = hit_radius
	query_shape.height = 0.8 + hit_radius * 2.0
	query.shape = query_shape
	query.collision_mask = 4

func begin() -> void:
	if attacking:
		return
	previous_transform = global_transform
	active = false
	attack_id += 1
	elapsed = 0.0
	combo_index = -1
	attacking = true
	hit_targets.clear()
	attack_event.emit("start", attack_id)

func finish() -> void:
	if not attacking:
		return
	active = false
	attacking = false
	attack_event.emit("end", attack_id)

func _physics_process(delta: float) -> void:
	if not attacking:
		return
	if hit_pause > 0.0:
		hit_pause = maxf(0.0, hit_pause - delta)
		return
	elapsed += delta
	var enabled := elapsed >= active_start and elapsed < active_end
	if not combo_windows.is_empty():
		enabled = false
		for index in range(combo_windows.size()):
			if elapsed >= combo_windows[index].x and elapsed < combo_windows[index].y:
				enabled = true
				if index != combo_index:
					combo_index = index
					hit_targets.clear()
				break
	if enabled != active:
		active = enabled
		attack_event.emit("active" if active else "recovery", attack_id)
	if active:
		query_shape.radius = hit_radius
		var travel := previous_transform.origin.distance_to(global_position)
		var angle := previous_transform.basis.get_rotation_quaternion().angle_to(global_basis.get_rotation_quaternion())
		var steps := clampi(int(ceil((travel + absf(angle)) / hit_radius)), 1, 64)
		for step in range(steps + 1):
			var sampled := previous_transform.interpolate_with(global_transform, float(step) / steps)
			query.transform = sampled
			query.transform.origin = sampled * Vector3(0, 0.58, 0)
			for result in get_world_3d().direct_space_state.intersect_shape(query):
				var target: Object = result.collider
				if target.has_method("receive_hit") and not hit_targets.has(target.get_instance_id()):
					hit_targets[target.get_instance_id()] = true
					target.receive_hit(damage)
					hit_confirmed.emit(query.transform.origin)
	previous_transform = global_transform
	if elapsed >= duration:
		finish()
