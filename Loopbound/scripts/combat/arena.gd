extends "res://scripts/main.gd"
func build_arena() -> void:
	var world := WorldEnvironment.new()
	world.environment = Environment.new()
	world.environment.background_mode = Environment.BG_SKY
	world.environment.sky = Sky.new()
	var sky_material := ProceduralSkyMaterial.new()
	sky_material.sky_top_color = Color("448bd0")
	sky_material.sky_horizon_color = Color("c6dff0")
	sky_material.ground_horizon_color = Color("c6dff0")
	world.environment.sky.sky_material = sky_material
	world.environment.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	world.environment.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	add_child(world)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-45, -35, 0)
	sun.shadow_enabled = true
	add_child(sun)
	block("Ground", Vector3(50, 1, 50), Vector3(0,-0.5,0), Color("84947b"))
	var dummy := StaticBody3D.new()
	dummy.set_script(preload("res://scripts/combat/dummy.gd"))
	dummy.name = "TrainingDummy"
	dummy.position = Vector3(-5,0,-3)
	add_child(dummy)
	var future := Marker3D.new()
	future.name = "FutureEnemySpawn"
	future.position = Vector3(10,0,0)
	add_child(future)
	for entry in [["训练木桩", Vector3(-5,0.05,-5)], ["敌人生成预留区", Vector3(10,0.05,-5)]]:
		var sign := Label3D.new()
		sign.text = entry[0]
		sign.position = entry[1]
		sign.rotation_degrees.x = -90
		sign.font_size = 64
		add_child(sign)
	var hud := CanvasLayer.new()
	var hint := Label.new()
	hint.text = "WASD 横移/前后移动  ·  鼠标 转向  ·  Shift 加速  ·  空格 闪避  ·  左键 / J 三连击  ·  Esc 释放鼠标"
	hint.position = Vector2(24,24)
	hud.add_child(hint)
	add_child(hud)
func build_player() -> void:
	super.build_player()
	player.position = Vector3.ZERO
	var combat := Node.new()
	combat.name = "Combat"
	combat.set_script(preload("res://scripts/combat/player_combat.gd"))
	player.add_child(combat)
