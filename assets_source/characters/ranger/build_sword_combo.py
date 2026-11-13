import bpy,math,json
from pathlib import Path
from mathutils import Matrix,Quaternion,Vector
ROOT=Path(r'D:/codex项目/3D');out=ROOT/'local_previews/combat/combo';out.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'assets_source/characters/ranger/locomotion_v3.blend'))
scene=bpy.context.scene;rig=next(o for o in scene.objects if o.type=='ARMATURE')
for t in rig.animation_data.nla_tracks:t.mute=t.name!='idle'
scene.frame_set(1)
neutral={b.name:b.matrix_basis.copy() for b in rig.pose.bones}
rest={b.name:b.matrix_local.to_quaternion() for b in rig.data.bones}
original=set(scene.objects)
bpy.ops.import_scene.gltf(filepath=str(next((ROOT/'assets_source/characters/ranger/animation_inputs/quaternius_ual2').rglob('UAL2_Standard.glb'))))
ref=next(o for o in scene.objects if o not in original and o.type=='ARMATURE')
conversion=Matrix.Rotation(math.pi,4,'Z')
refrest={b.name:(conversion@b.matrix_local).to_quaternion() for b in ref.data.bones}
for t in ref.animation_data.nla_tracks:t.mute=t.name!='Sword_Regular_Combo'
ref.animation_data.action=None
mapping={'Hip':'pelvis','Waist':'spine_01','Spine01':'spine_02','Spine02':'spine_03','NeckTwist01':'neck_01','Head':'Head'}
for side,ending in [('L','l'),('R','r')]:
 for dst,src in [('Clavicle','clavicle'),('Upperarm','upperarm'),('Forearm','lowerarm'),('Hand','hand'),('Thigh','thigh'),('Calf','calf'),('Foot','foot'),('ToeBase','ball')]:mapping[side+'_'+dst]=src+'_'+ending
samples=[]
leg_directions=[]
# Reference imports at 24fps: 72 frames = 3 seconds. Compress to 2 seconds.
for f in range(61):
 source=1+72*f/60;scene.frame_set(int(source),subframe=source%1)
 samples.append({n:conversion@ref.pose.bones[n].matrix.copy() for n in mapping.values()})
 leg_directions.append({n:conversion.to_3x3() @ (ref.pose.bones[n].tail-ref.pose.bones[n].head) for n in mapping.values() if n.startswith(("thigh_", "calf_"))})
for o in list(scene.objects):
 if o not in original:bpy.data.objects.remove(o,do_unlink=True)
rig.animation_data_clear();rig.animation_data_create();action=bpy.data.actions.new('Sword_Combo');rig.animation_data.action=action
ordered=sorted(mapping,key=lambda n:len(rig.pose.bones[n].parent_recursive))
scale=rig.data.bones['Hip'].head_local.z / samples[0]['pelvis'].translation.z
for f,pose in enumerate(samples):
 scene.frame_set(f+1)
 for b in rig.pose.bones:b.matrix_basis=neutral[b.name];b.rotation_mode='QUATERNION'
 bpy.context.view_layer.update()
 for name in ordered:
  b=rig.pose.bones[name];src=mapping[name]
  q=pose[src].to_quaternion() @ refrest[src].inverted() @ rest[name]
  if name.endswith(("_Thigh","_Calf")):
   axis=b.bone.tail_local-b.bone.head_local
   q=axis.normalized().rotation_difference(leg_directions[f][src].normalized()) @ rest[name]
  pos=b.head.copy()
  if name=='Hip':
   p=pose[src].translation*scale
   pos=Vector((p.x,p.y-samples[0][src].translation.y*scale,p.z))
  b.matrix=Matrix.Translation(pos)@q.to_matrix().to_4x4();bpy.context.view_layer.update()
 # Preserve the fitted grip, independently of the source's hand proportions.
 for finger in ['Index','Middle','Ring','Little','Thumb']:
  for seg in range(3):
   q=Quaternion((1,0,0),-math.radians(([25,55,40] if finger=='Thumb' else [65,90,60])[seg]))
   if finger=='Thumb' and seg==0:q=Quaternion((0,0,1),-.52)@q
   rig.pose.bones[f'R_{finger}{seg+1:02}'].rotation_quaternion=q
 for b in rig.pose.bones:
  b.keyframe_insert('location',frame=f+1);b.keyframe_insert('rotation_quaternion',frame=f+1);b.keyframe_insert('scale',frame=f+1)
scene.render.fps=30;scene.frame_start=1;scene.frame_end=61;scene.frame_set(1)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'assets_source/characters/ranger/Sword_Combo.blend'))
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(ROOT/'Loopbound/assets/animations/Sword_Combo.glb'),export_format='GLB',use_selection=True,export_animation_mode='ACTIVE_ACTIONS',export_frame_range=True,export_force_sampling=True)
print('COMBO RETARGETED',len(rig.data.bones))
