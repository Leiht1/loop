import bpy,math,json
from pathlib import Path
from mathutils import Quaternion, Euler, Vector, Matrix
ROOT=Path(r'D:/codex项目/3D')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'assets_source/characters/ranger/locomotion_v3.blend'))
scene=bpy.context.scene; rig=next(o for o in scene.objects if o.type=='ARMATURE')
for t in rig.animation_data.nla_tracks: t.mute=t.name!='idle'
scene.frame_set(1)
neutral={b.name:b.matrix_basis.copy() for b in rig.pose.bones}
rests={b.name:list(sum((list(row) for row in b.matrix_local),[])) for b in rig.data.bones}
rig.animation_data_clear();rig.animation_data_create()
a=bpy.data.actions.new('Attack_01');rig.animation_data.action=a
# Small, ordered torso rotations lead the arm. Local axes match the existing rig.
keys={
'Waist':[(0,0,0),(0,-.10,0),(0,.14,0),(0,.18,0),(0,.15,0)],
'Spine02':[(0,0,0),(-.05,-.16,0),(.08,.18,0),(.10,.22,0),(.06,.18,0)],
'R_Upperarm':[(0,0,0),(1.65,-.25,-.55),(1.0,.35,.25),(.55,.45,.65),(.45,.35,.65)],
'R_Forearm':[(0,0,0),(.65,0,-.05),(.22,0,0),(.22,0,0),(.4,0,0)],
'R_Hand':[(0,0,0),(.15,0,-.12),(-.55,0,.10),(-.85,0,.10),(-.75,0,.10)],
'L_Upperarm':[(0,0,0),(.15,0,.25),(.25,0,.35),(.2,0,.25),(.1,0,.15)],
'L_Forearm':[(0,0,0),(.35,0,0),(.45,0,0),(.4,0,0),(.3,0,0)]}
times=[0,.12,.28,.38,.50]
scene.render.fps=30;scene.frame_start=1;scene.frame_end=16
for i,time in enumerate(times):
 frame=1+time*30
 for b in rig.pose.bones:
  b.matrix_basis=neutral[b.name]
  b.rotation_mode='QUATERNION'
  if b.name in keys: b.rotation_quaternion=b.rotation_quaternion @ Euler(keys[b.name][i]).to_quaternion()
  if b.name.startswith('R_'):
   for finger in ['Index','Middle','Ring','Little','Thumb']:
    if b.name.startswith('R_'+finger):
     segment=int(b.name[-2:])-1
     angle=([25,55,40] if finger=='Thumb' else [65,90,60])[segment]
     q=Quaternion((1,0,0),-math.radians(angle))
     if finger=='Thumb' and segment==0:q=Quaternion((0,0,1),-.52)@q
     b.rotation_quaternion=q
 bpy.context.view_layer.update()
 if i > 0:
  target=Vector([(0,0,0),(.36,.16,1.44),(.02,.43,1.17),(-.12,.34,1.04),(-.15,.30,1.01)][i])
  upper=rig.pose.bones['R_Upperarm']; fore=rig.pose.bones['R_Forearm']; hand=rig.pose.bones['R_Hand']
  shoulder=upper.head.copy(); axis=target-shoulder; distance=min(axis.length,upper.length+fore.length-.005); axis.normalize()
  pole=Vector((1,-.3,-.4)); pole=(pole-axis*pole.dot(axis)).normalized()
  along=(upper.length**2-fore.length**2+distance**2)/(2*distance)
  elbow=shoulder+axis*along+pole*math.sqrt(max(0,upper.length**2-along**2))
  for bone,end in [(upper,elbow),(fore,target)]:
   q=(bone.tail-bone.head).rotation_difference(end-bone.head)
   matrix=q.to_matrix().to_4x4() @ bone.matrix
   matrix.translation=bone.head.copy();bone.matrix=matrix;bpy.context.view_layer.update()
  z=Vector([(0,0,1),(.35,-.05,.94),(-.65,.65,-.38),(-.65,.35,-.68),(-.65,.30,-.70)][i]).normalized()
  y=Vector((0,0,-1));y=(y-z*y.dot(z)).normalized();x=y.cross(z).normalized()
  matrix=Matrix((x,y,z)).transposed().to_4x4();matrix.translation=hand.head.copy();hand.matrix=matrix
  bpy.context.view_layer.update()
 for b in rig.pose.bones:
  b.keyframe_insert('location',frame=frame,group=b.name)
  b.keyframe_insert('rotation_quaternion',frame=frame,group=b.name)
  b.keyframe_insert('scale',frame=frame,group=b.name)
for layer in a.layers:
 for strip in layer.strips:
  for bag in strip.channelbags:
   for fc in bag.fcurves:
    for k in fc.keyframe_points:k.interpolation='BEZIER';k.handle_left_type='AUTO_CLAMPED';k.handle_right_type='AUTO_CLAMPED'
scene.frame_set(1)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'assets_source/characters/ranger/Attack_01.blend'))
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.gltf(filepath=str(ROOT/'Loopbound/assets/animations/Attack_01.glb'),export_format='GLB',use_selection=True,export_animation_mode='ACTIVE_ACTIONS',export_frame_range=True,export_force_sampling=True)
assert len(rig.data.bones)==71
assert rests=={b.name:list(sum((list(row) for row in b.matrix_local),[])) for b in rig.data.bones}
print('ATTACK_01: 71 bones, rest unchanged, keys',times)
