extends StaticBody3D
@export var max_health := 100.0
var health := 100.0
var label: Label3D
var material: StandardMaterial3D
var flash := 0.0
var body_mesh: MeshInstance3D
var recoil := 0.0
func _ready() -> void:
	collision_layer = 4
	collision_mask = 0
	material = StandardMaterial3D.new()
	material.albedo_color = Color("936342")
	var mesh := MeshInstance3D.new()
	var cylinder := CylinderMesh.new()
	cylinder.top_radius = 0.23
	cylinder.bottom_radius = 0.3
	cylinder.height = 1.7
	body_mesh = mesh
	mesh.mesh = cylinder
	mesh.position.y = 0.85
	mesh.material_override = material
	add_child(mesh)
	var collision := CollisionShape3D.new()
	var shape := CylinderShape3D.new()
	shape.radius = 0.3
	shape.height = 1.7
	collision.shape = shape
	collision.position.y = 0.85
	add_child(collision)
	label = Label3D.new()
	label.position.y = 2.1
	label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	add_child(label)
	health = max_health
	update_label()
func update_label() -> void:
	label.text = "Training  %d / %d" % [health, max_health]
func receive_hit(amount: float) -> void:
	health = maxf(0, health - amount)
	flash = 0.25
	recoil = 1.0
	update_label()
func _process(delta: float) -> void:
	flash = maxf(0, flash - delta)
	recoil = move_toward(recoil, 0.0, delta * 6.0)
	body_mesh.rotation.z = sin(recoil * PI * 2.0) * recoil * 0.12
	material.albedo_color = Color("ffdf79") if flash > 0 else Color("936342")
	if health <= 0 and flash == 0:
		health = max_health
		update_label()
