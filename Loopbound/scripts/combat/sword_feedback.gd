extends Node3D
var weapon: Node3D
var ribbon := ImmediateMesh.new()
var samples: Array = []
var sound := AudioStreamPlayer.new()
func _ready() -> void:
 weapon = get_parent()
 var visual := MeshInstance3D.new()
 visual.mesh = ribbon
 var mat := StandardMaterial3D.new()
 mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
 mat.vertex_color_use_as_albedo = true
 mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
 mat.cull_mode = BaseMaterial3D.CULL_DISABLED
 visual.material_override = mat
 add_child(visual)
 visual.top_level = true
 visual.global_transform = Transform3D.IDENTITY
 add_child(sound)
 sound.stream = load("res://assets/animations/sword_hit.wav")
 sound.volume_db = -12
 weapon.hit_confirmed.connect(on_hit)
func on_hit(_position: Vector3) -> void:
 sound.pitch_scale = 0.95 + weapon.combo_index * 0.07
 sound.play()
func _process(delta: float) -> void:
 for sample in samples: sample[2] -= delta
 while not samples.is_empty() and samples[0][2] <= 0: samples.pop_front()
 if weapon.active:
  samples.append([weapon.to_global(Vector3(0,0.2,0)),weapon.to_global(Vector3(0,1.02,0)),0.085])
 ribbon.clear_surfaces()
 if samples.size() < 2: return
 ribbon.surface_begin(Mesh.PRIMITIVE_TRIANGLES)
 for i in range(1,samples.size()):
  var a = samples[i-1]
  var b = samples[i]
  ribbon.surface_set_color(Color(0.45,0.85,1.0,0.35 * a[2]/0.085))
  for point in [a[0],a[1],b[1],a[0],b[1],b[0]]: ribbon.surface_add_vertex(point)
 ribbon.surface_end()