extends Node

@export var animation_tree: AnimationTree
@export var blend_parameter := "parameters/locomotion/blend_position"
@export var idle_look_delay := 5.0
var idle_elapsed := 0.0
var dodge_node: AnimationNodeAnimation
var state := "idle"
var motion_direction := Vector2.ZERO
var fast_strafe := false
var blended_direction := Vector2.ZERO

func cancel_turn() -> void:
	animation_tree.set("parameters/turn/request", AnimationNodeOneShot.ONE_SHOT_REQUEST_ABORT)

func play_turn(degrees: int) -> float:
	var graph := animation_tree.tree_root as AnimationNodeBlendTree
	var node := graph.get_node("turn_clip") as AnimationNodeAnimation
	node.animation = "turn_left" if degrees > 0 else "turn_right"
	animation_tree.set("parameters/turn/request", AnimationNodeOneShot.ONE_SHOT_REQUEST_FIRE)
	var clips := animation_tree.get_node(animation_tree.anim_player) as AnimationPlayer
	return clips.get_animation(node.animation).length


func update_motion(speed: float, delta: float) -> void:
	state = "idle" if speed < 0.1 else ("run" if motion_direction.y > 2.3 and not fast_strafe else "walk")
	if is_instance_valid(animation_tree):
		var target := motion_direction if speed >= 0.1 else Vector2.ZERO
		if fast_strafe:
			target = target.limit_length(2.0)
		blended_direction = blended_direction.lerp(target, 1.0 - exp(-15.0 * delta))
		animation_tree.set(blend_parameter, blended_direction)
		animation_tree.set("parameters/motion_rate/scale", 1.5 if fast_strafe and speed > 0.1 else 1.0)
		if speed >= 0.1:
			idle_elapsed = 0.0
			animation_tree.set("parameters/idle_variation/request", AnimationNodeOneShot.ONE_SHOT_REQUEST_FADE_OUT)
		elif animation_tree.get("parameters/idle_variation/active") or animation_tree.get("parameters/evasion/active"):
			idle_elapsed = 0.0
		else:
			idle_elapsed += delta
			if idle_elapsed >= idle_look_delay:
				idle_elapsed = 0.0
				animation_tree.set("parameters/idle_variation/request", AnimationNodeOneShot.ONE_SHOT_REQUEST_FIRE)

func play_dodge(direction: String) -> void:
	animation_tree.set("parameters/turn/request", AnimationNodeOneShot.ONE_SHOT_REQUEST_FADE_OUT)
	idle_elapsed = 0.0
	animation_tree.set("parameters/idle_variation/request", AnimationNodeOneShot.ONE_SHOT_REQUEST_FADE_OUT)
	dodge_node.animation = "dodge_" + direction
	animation_tree.set("parameters/evasion/request", AnimationNodeOneShot.ONE_SHOT_REQUEST_FIRE)
