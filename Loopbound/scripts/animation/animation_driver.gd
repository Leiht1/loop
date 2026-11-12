extends Node

@export var animation_tree: AnimationTree
@export var blend_parameter := "parameters/locomotion/blend_position"
var state := "idle"
var blended_speed := 0.0

func update_motion(speed: float, delta: float) -> void:
	blended_speed = lerpf(blended_speed, speed, 1.0 - exp(-15.0 * delta))
	state = "idle" if speed < 0.1 else ("walk" if speed < 3.3 else "run")
	if is_instance_valid(animation_tree):
		animation_tree.set(blend_parameter, blended_speed)
