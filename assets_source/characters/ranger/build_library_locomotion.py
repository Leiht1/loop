import sys
arguments = sys.argv[sys.argv.index('--')+1:]
source_clip, output_clip = arguments[:2]
original_turn = '--original-turn' in arguments[2:]
import bpy,math,json
from pathlib import Path
from mathutils import Matrix,Quaternion,Vector
ROOT=Path(r'D:/codex项目/3D');out=ROOT/'local_previews/combat/locomotion_library';out.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'assets_source/characters/ranger/locomotion_v3.blend'))
scene=bpy.context.scene;rig=next(o for o in scene.objects if o.type=='ARMATURE')
for t in rig.animation_data.nla_tracks:t.mute=t.name!='idle'
scene.frame_set(1)
neutral={b.name:b.matrix_basis.copy() for b in rig.pose.bones}
rest={b.name:b.matrix_local.to_quaternion() for b in rig.data.bones}
original=set(scene.objects)
input_path=ROOT/('assets_source/characters/ranger/animation_inputs/kinemiq/'+source_clip+'.glb')
bpy.ops.import_scene.gltf(filepath=str(input_path if input_path.exists() else next((ROOT/'assets_source/characters/ranger/animation_inputs/quaternius_ual1').rglob('UAL1_Standard.glb'))))
ref=next(o for o in scene.objects if o not in original and o.type=='ARMATURE')
conversion=Matrix.Rotation(math.pi,4,'Z')
refrest={b.name:(conversion@b.matrix_local).to_quaternion() for b in ref.data.bones}
for t in ref.animation_data.nla_tracks:t.mute=t.name!=(ref.animation_data.nla_tracks[0].name if input_path.exists() else source_clip)
track=next(t for t in ref.animation_data.nla_tracks if t.name==(ref.animation_data.nla_tracks[0].name if input_path.exists() else source_clip))
source_start=min(s.frame_start for s in track.strips)
source_end=max(s.frame_end for s in track.strips)
frames=round((source_end-source_start)/scene.render.fps*30)
ref.animation_data.action=None
mapping={'Hip':'pelvis','Waist':'spine_01','Spine01':'spine_02','Spine02':'spine_03','NeckTwist01':'neck_01','Head':'Head'}
for side,ending in [('L','l'),('R','r')]:
 for dst,src in [('Clavicle','clavicle'),('Upperarm','upperarm'),('Forearm','lowerarm'),('Hand','hand'),('Thigh','thigh'),('Calf','calf'),('Foot','foot'),('ToeBase','ball')]:mapping[side+'_'+dst]=src+'_'+ending
samples=[]
leg_directions=[]
# Reference imports at 24fps: 72 frames = 3 seconds. Compress to 2 seconds.
for f in range(frames+1):
 source=source_start+(source_end-source_start)*f/frames;scene.frame_set(int(source),subframe=source%1)
 samples.append({n:conversion@ref.pose.bones[n].matrix.copy() for n in mapping.values()})
 leg_directions.append({n:conversion.to_3x3() @ (ref.pose.bones[n].tail-ref.pose.bones[n].head) for n in mapping.values() if n.startswith(('thigh_', 'calf_'))})
if output_clip.startswith('Library_Turn') and not original_turn:
 # Extract heading from the projected forward axis. Pelvis Euler angles can
 # flip near the imported rig's vertical-axis singularity.
 headings=[]
 for pose in samples:
  rotation=pose['pelvis'].to_quaternion() @ refrest['pelvis'].inverted()
  forward=rotation @ Vector((0,1,0))
  heading=math.atan2(-forward.x,forward.y)
  if headings:
   heading=headings[-1]+(heading-headings[-1]+math.pi)%(2*math.pi)-math.pi
  headings.append(heading)
 for index,pose in enumerate(samples):
  correction=Matrix.Rotation(-(headings[index]-headings[0]),4,'Z')
  samples[index]={name:correction@matrix for name,matrix in pose.items()}
  leg_directions[index]={name:correction.to_3x3()@axis for name,axis in leg_directions[index].items()}
for o in list(scene.objects):
 if o not in original:bpy.data.objects.remove(o,do_unlink=True)
rig.animation_data_clear();rig.animation_data_create();action=bpy.data.actions.new(output_clip);rig.animation_data.action=action
ordered=sorted(mapping,key=lambda n:len(rig.pose.bones[n].parent_recursive))
scale=rig.data.bones['Hip'].head_local.z / samples[0]['pelvis'].translation.z
for f,pose in enumerate(samples):
 scene.frame_set(f+1)
 for b in rig.pose.bones:b.matrix_basis=neutral[b.name];b.rotation_mode='QUATERNION'
 bpy.context.view_layer.update()
 for name in ordered:
  b=rig.pose.bones[name];src=mapping[name]
  q=pose[src].to_quaternion() @ refrest[src].inverted() @ rest[name]
  if name.endswith(('_Thigh','_Calf')):
   axis=b.bone.tail_local-b.bone.head_local
   target_axis=leg_directions[f][src].normalized()
   if output_clip.startswith('Library_Turn') or original_turn:
    mapped_axis=q @ (rest[name].inverted() @ axis.normalized())
    q=mapped_axis.rotation_difference(target_axis) @ q
   else:
    q=axis.normalized().rotation_difference(target_axis) @ rest[name]
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
# Align the lowest sole contact across the clip to the floor, preserving airborne phases.
meshes=[o for o in scene.objects if o.type=='MESH' and any(m.type=='ARMATURE' and m.object==rig for m in o.modifiers)]
floor=float('inf')
for frame in range(1,frames+2,3):
 scene.frame_set(frame)
 for obj in meshes:
  evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
  mesh=evaluated.to_mesh()
  floor=min(floor,min((evaluated.matrix_world@v.co).z for v in mesh.vertices))
  evaluated.to_mesh_clear()
for frame in range(1,frames+2):
 scene.frame_set(frame)
 root=rig.pose.bones['Root']
 matrix=root.matrix.copy();matrix.translation.z-=floor
 root.matrix=matrix
 root.keyframe_insert('location',frame=frame)
scene.render.fps=30;scene.frame_start=1;scene.frame_end=frames+1;scene.frame_set(1)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/('assets_source/characters/ranger/'+output_clip+'.blend')))
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(ROOT/('Loopbound/assets/animations/'+output_clip+'.glb')),export_format='GLB',use_selection=True,export_animation_mode='ACTIVE_ACTIONS',export_frame_range=True,export_force_sampling=True)
print('LIBRARY RETARGETED',len(rig.data.bones))
