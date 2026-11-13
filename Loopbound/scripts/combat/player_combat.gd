extends Node
# Single-handed descending cut, authored independently of locomotion clips.
@export var dodge_cancel_time := 0.18
var weapon: Node3D
var skeleton: Skeleton3D
var controller: CharacterBody3D
func _ready() -> void:
	controller = get_parent()
	skeleton = controller.visual.find_children("*", "Skeleton3D", true, false)[0]
	var attachment := BoneAttachment3D.new()
	attachment.name = "RightHandWeaponSocket"
	attachment.bone_name = "R_Hand"
	assert(skeleton.find_bone(attachment.bone_name) >= 0)
	skeleton.add_child(attachment)
	weapon = Node3D.new()
	weapon.name = "StraightSword"
	weapon.set_script(preload("res://scripts/combat/weapon.gd"))
	attachment.add_child(weapon)
	# Hand origin is the wrist; move the grip into the curled palm.
	weapon.position = Vector3(0.0, 0.055, -0.025)
	weapon.basis = Basis(Vector3.FORWARD, PI / 2.0)
	weapon.add_child(preload("res://scenes/test/straight_sword_model.tscn").instantiate())
	weapon.duration = 2.16
	weapon.combo_windows.assign([Vector2(0.22,0.36), Vector2(0.48,0.66), Vector2(1.23,1.46)])
	weapon.active_start = 0.24
	weapon.active_end = 0.38
	install_attack()
	weapon.add_child(preload("res://scripts/combat/sword_feedback.gd").new())
	if not InputMap.has_action("attack"):
		InputMap.add_action("attack")
		var key := InputEventKey.new()
		key.physical_keycode = KEY_J
		InputMap.action_add_event("attack", key)
		var mouse := InputEventMouseButton.new()
		mouse.button_index = MOUSE_BUTTON_LEFT
		InputMap.action_add_event("attack", mouse)
func install_attack() -> void:
	var tree: AnimationTree = controller.animation_driver.animation_tree
	var clips := tree.get_node(tree.anim_player) as AnimationPlayer
	clips.get_animation_library("").add_animation("sword_light_cut", preload("res://assets/animations/sword_light_cut_legacy.tres"))
	var playback := preload("res://assets/animations/Sword_Combo.tres").duplicate(true) as Animation
	# Open the armed shoulder and bend the elbow before reusing the idle pose.
	for idle_name in ["idle", "look_around"]:
		var idle_clip := clips.get_animation(idle_name)
		for track in range(idle_clip.get_track_count()):
			if idle_clip.track_get_type(track) != Animation.TYPE_ROTATION_3D:
				continue
			var bone := String(idle_clip.track_get_path(track)).get_slice(":", 1)
			var offset := Vector3.ZERO
			if bone == "R_Upperarm": offset = Vector3(0.12, 0.0, -0.48)
			elif bone == "R_Forearm": offset = Vector3(0.40, 0.0, 0.0)
			else: continue
			for key in range(idle_clip.track_get_key_count(track)):
				var rotation: Quaternion = idle_clip.track_get_key_value(track, key)
				idle_clip.track_set_key_value(track, key, rotation * Quaternion.from_euler(offset))
	var idle := clips.get_animation("idle")
	playback.length = 2.16
	for t in range(playback.get_track_count()):
		var idle_track := idle.find_track(playback.track_get_path(t), playback.track_get_type(t))
		if idle_track >= 0 and idle.track_get_key_count(idle_track) > 0:
			playback.track_insert_key(t, 2.16, idle.track_get_key_value(idle_track, 0))
	clips.get_animation_library("").add_animation("Sword_Combo_Playback", playback)
	for clip_name in clips.get_animation_list():
		var clip := clips.get_animation(clip_name)
		for t in range(clip.get_track_count()):
			var digit := String(clip.track_get_path(t)).get_slice(":", 1)
			if clip.track_get_type(t) != Animation.TYPE_ROTATION_3D or not digit.begins_with("R_"):
				continue
			for finger in ["Index", "Middle", "Ring", "Little", "Thumb"]:
				if digit.begins_with("R_" + finger):
					var segment := int(digit.right(2)) - 1
					var angles := [25.0,55.0,40.0] if finger == "Thumb" else [65.0,90.0,60.0]
					var grip := Quaternion(Vector3.RIGHT, deg_to_rad(angles[segment]))
					if finger == "Thumb" and segment == 0:
						grip = Quaternion(Vector3.BACK, -0.52) * grip
					for k in range(clip.track_get_key_count(t)):
						clip.track_set_key_value(t, k, grip)
	# Keep the armed right arm outside the leg swing envelope. Preserve a
	# small amount of the source swing; do not alter legs, root or attack.
	var neutral := clips.get_animation("idle")
	for clip_name in ["walk", "run", "walk_left", "walk_right", "walk_back", "turn_left", "turn_right"]:
		var clip := clips.get_animation(clip_name)
		for t in range(clip.get_track_count()):
			if clip.track_get_type(t) != Animation.TYPE_ROTATION_3D:
				continue
			var bone := String(clip.track_get_path(t)).get_slice(":", 1)
			if bone not in ["R_Upperarm", "R_Forearm", "R_Hand"]:
				continue
			var base_track := neutral.find_track(clip.track_get_path(t), Animation.TYPE_ROTATION_3D)
			if base_track < 0:
				continue
			var base: Quaternion = neutral.track_get_key_value(base_track, 0)
			var offset := Vector3.ZERO
			for k in range(clip.track_get_key_count(t)):
				var source: Quaternion = clip.track_get_key_value(t, k)
				clip.track_set_key_value(t, k, base.slerp(source, 0.15) * Quaternion.from_euler(offset))
	var graph := tree.tree_root as AnimationNodeBlendTree
	var attack := AnimationNodeAnimation.new()
	attack.animation = "Sword_Combo_Playback"
	var shot := AnimationNodeOneShot.new()
	shot.fadein_time = 0.04
	shot.fadeout_time = 0.0
	graph.add_node("light_attack", attack)
	graph.add_node("combat", shot)
	graph.disconnect_node("output", 0)
	graph.connect_node("combat", 0, "evasion")
	graph.connect_node("combat", 1, "light_attack")
	graph.connect_node("output", 0, "combat")

func begin() -> void:
	if weapon.attacking or controller.dodging or not controller.is_on_floor():
		return
	weapon.begin()
	var tree: AnimationTree = controller.animation_driver.animation_tree
	tree.set("parameters/idle_variation/request", AnimationNodeOneShot.ONE_SHOT_REQUEST_FADE_OUT)
	tree.set("parameters/combat/request", AnimationNodeOneShot.ONE_SHOT_REQUEST_FIRE)

func finish() -> void:
	controller.animation_driver.animation_tree.set("parameters/combat/request", AnimationNodeOneShot.ONE_SHOT_REQUEST_FADE_OUT)
	weapon.finish()

func _physics_process(_delta: float) -> void:
	if Input.is_action_just_pressed("attack"):
		begin()
