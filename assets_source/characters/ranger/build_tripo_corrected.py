"""Preserve Tripo skin and 41-bone hierarchy; symmetrize rest joints and bake diagnostic motion."""
import bpy,math,json,sys
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
R=Path(__file__).resolve().parents[3]
HYBRID='--hybrid' in sys.argv
variant='tripo_hybrid' if HYBRID else 'tripo_corrected'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(R/'assets_source/characters/ranger/animation_inputs/tripo_rigged_original.glb'))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH' and any(m.type=='ARMATURE' for m in o.modifiers)]
rot=Matrix.Rotation(math.pi/2,4,'Z')
coords=[rot@o.matrix_world@v.co for o in meshes for v in o.data.vertices]
lo=Vector([min(v[i] for v in coords) for i in range(3)]);hi=Vector([max(v[i] for v in coords) for i in range(3)])
scale=1.8/(hi.z-lo.z);center=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z))
transform=Matrix.Scale(scale,4)@Matrix.Translation(-center)@rot
# Bake normalization into geometry and armature rest data, preserving vertex groups.
for o in meshes:
 world=transform@o.matrix_world
 for v in o.data.vertices:v.co=world@v.co
 o.parent=None;o.matrix_world=Matrix.Identity(4)
rig.data.transform(transform@rig.matrix_world);rig.matrix_world=Matrix.Identity(4)
for o in meshes:o.parent=rig
bpy.context.view_layer.objects.active=rig;rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT');eb=rig.data.edit_bones
before={b.name:{'head':list(b.head),'tail':list(b.tail)} for b in eb}
for b in list(eb):
 if not b.name.startswith('L_'):continue
 other=eb.get('R_'+b.name[2:])
 if not other:continue
 for attr in ['head','tail']:
  l=getattr(b,attr).copy();rr=getattr(other,attr).copy();rr.x=-rr.x
  mean=(l+rr)/2;setattr(b,attr,mean);mirror=mean.copy();mirror.x=-mirror.x;setattr(other,attr,mirror)
for b in eb:
 if not b.name.startswith(('L_','R_')):
  b.head.x=0;b.tail.x=0
# Root/Hip are transform helpers, not anatomical diagonals.
eb['Root'].tail=eb['Root'].head+Vector((0,0,.10))
eb['Hip'].tail=eb['Hip'].head+Vector((0,0,.10))
after={b.name:{'head':list(b.head),'tail':list(b.tail)} for b in eb}
bpy.ops.object.mode_set(mode='OBJECT')
scene=bpy.context.scene;scene.render.fps=30
rig.animation_data_clear();rig.animation_data_create()
for p in rig.pose.bones:p.rotation_mode='QUATERNION'
reference=None
if HYBRID:
 with bpy.data.libraries.load(str(R/'assets_source/characters/ranger/comparison_triangles.blend'),link=False) as (src,dst):dst.objects=['Rig']
 reference=dst.objects[0];bpy.context.collection.objects.link(reference)
 reference.name='OldMotionReference'
 reference.animation_data.action=None


def set_world(name,head,direction):
 p=rig.pose.bones[name];b=p.bone
 q=(b.tail_local-b.head_local).normalized().rotation_difference(direction.normalized())
 p.matrix=Matrix.Translation(head)@q.to_matrix().to_4x4()@b.matrix_local.to_quaternion().to_matrix().to_4x4()
 bpy.context.view_layer.update()

def world_turn(name,axis,angle):
 p=rig.pose.bones[name];m=p.matrix.copy();p.matrix=Matrix.Translation(m.translation)@Quaternion(Vector(axis),angle).to_matrix().to_4x4()@m.to_quaternion().to_matrix().to_4x4();bpy.context.view_layer.update()

def leg(side,target,foot_pitch=0):
 thigh=rig.pose.bones[side+'_Thigh'];calf=rig.pose.bones[side+'_Calf']
 hip=thigh.head.copy();l1=thigh.bone.length;l2=calf.bone.length
 delta=target-hip;dist=min(delta.length,l1+l2-.001);axis=delta.normalized()
 forward=Vector(((-1 if side=='L' else 1)*.14 if HYBRID else 0,1,0));pole=(forward-axis*forward.dot(axis)).normalized()
 along=(l1*l1-l2*l2+dist*dist)/(2*dist);height=math.sqrt(max(0,l1*l1-along*along))
 knee=hip+axis*along+pole*height
 set_world(side+'_Thigh',hip,knee-hip);set_world(side+'_Calf',knee,target-knee)
 foot=rig.pose.bones[side+'_Foot'];rest=foot.bone
 set_world(foot.name,target,Quaternion(Vector((1,0,0)),foot_pitch)@(rest.tail_local-rest.head_local))
 if HYBRID:world_turn(foot.name,(0,0,1),(1 if side=='L' else -1)*math.radians(4))

checks={};durations={'idle':90,'walk':36,'run':24,'arms_overhead':120,'elbow_bend':90,'deep_squat':120}
if HYBRID:durations={'idle':60,'walk':30,'run':22,'arms_overhead':60,'elbow_bend':60,'deep_squat':60}
for name,duration in durations.items():
 if HYBRID:
  for track in reference.animation_data.nla_tracks:track.mute=track.name!=name

 action=bpy.data.actions.new(name);rig.animation_data.action=action;checks[name]=[]
 for frame in range(duration+1):
  t=frame/duration;theta=t*math.tau;stress=math.sin(math.pi*t)**2
  if HYBRID:scene.frame_set(frame+1)
  for p in rig.pose.bones:p.matrix_basis=Matrix.Identity(4)
  bpy.context.view_layer.update()
  walk=name=='walk';run=name=='run';gait=walk or run
  drop=(-.045+.012*math.cos(2*theta)) if walk else (-.075+.028*math.cos(2*theta)) if run else -.30*stress if name=='deep_squat' else .002*math.sin(theta)
  if HYBRID:drop=reference.pose.bones['pelvis'].head.z-reference.data.bones['pelvis'].head_local.z
  hip=rig.pose.bones['Hip'];m=hip.matrix.copy();m.translation+=Vector((0,-.045*stress if HYBRID and name=='deep_squat' else -.08*stress if name=='deep_squat' else 0,drop));hip.matrix=m
  bpy.context.view_layer.update()
  if gait:
   world_turn('Hip',(0,0,1),(.012 if HYBRID else .035 if walk else .055)*math.sin(theta))
   world_turn('Spine01',(1,0,0),-.035 if walk else -.10)
   world_turn('Spine02',(0,0,1),(-.018 if HYBRID else -.045 if walk else -.075)*math.sin(theta))
  elif name=='deep_squat':world_turn('Spine01',(1,0,0),-.23*stress)
  elif name=='idle':world_turn('Spine02',(1,0,0),.008*math.sin(theta))
  if HYBRID:
   old=reference.pose.bones['chest'];set_world('Spine01',rig.pose.bones['Spine01'].head.copy(),old.tail-old.head)

  for side,sign,offset in [('L',-1,0),('R',1,.5)]:
   phase=(t+offset)%1;p=phase;duty=.6 if walk else .42
   footrest=rig.data.bones[side+'_Foot'].head_local.copy();target=footrest.copy();swing=0
   if gait:
    stride=.21 if walk else .32
    if p<duty:target.y+=stride*(1-2*p/duty)
    else:
     s=(p-duty)/(1-duty);smooth=s*s*(3-2*s);target.y+=stride*(-1+2*smooth);target.z+=(.105 if walk else .20)*math.sin(math.pi*s)**1.5
    swing=-(.30 if walk else .65)*math.cos(math.tau*p)
   pitch=0.0
   if gait:
    if p<duty:
     contact=p/duty;pitch=.16*max(0,1-contact/.22)-.30*max(0,(contact-.78)/.22)
    else:
     flight=(p-duty)/(1-duty);pitch=-.30*(1-flight)+.16*flight+.14*math.sin(math.pi*flight)
   if HYBRID:
    old_side='R' if side=='L' else 'L'
    old_foot=reference.pose.bones['foot.'+old_side]
    target=footrest+(old_foot.head-old_foot.bone.head_local)
    target.x=footrest.x
    pitch*=.28
   leg(side,target,pitch)
   # Keep boots on the floor during support; retain lift during swing.
   boot=min([o for o in meshes if o.name in ['tripo_part_3','tripo_part_5']], key=lambda o: abs(sum(v.co.x for v in o.data.vertices)/len(o.data.vertices)-footrest.x))
   deps=bpy.context.evaluated_depsgraph_get();ev=boot.evaluated_get(deps);mesh=ev.to_mesh();bottom=min((ev.matrix_world@v.co).z for v in mesh.vertices);ev.to_mesh_clear()
   support=(not gait) or (old_foot.head.z-old_foot.bone.head_local.z<.003 if HYBRID else p<duty)
   if support or bottom<0:
    target.z-=bottom;leg(side,target,pitch)
   # Clavicle contributes to overhead reach instead of rotating only the shoulder.
   if name=='arms_overhead':world_turn(side+'_Clavicle',(0,1,0),-sign*.32*stress)
   upper=rig.pose.bones[side+'_Upperarm'];head=upper.head.copy()
   elev=(math.radians(164)*stress if name=='arms_overhead' else .10)
   direction=Vector((sign*math.sin(elev),.12*math.sin(elev),-math.cos(elev))).normalized()
   direction=Quaternion(Vector((1,0,0)),swing if gait else .65*stress if name=='deep_squat' else 0)@direction
   if HYBRID:
    old_upper=reference.pose.bones['upper_arm.'+old_side];direction=(old_upper.tail-old_upper.head).normalized()
   set_world(upper.name,head,direction)
   elbow=rig.pose.bones[side+'_Forearm'].head.copy()
   bend=(.23+.10*math.sin(math.tau*p)) if walk else (1.15+.18*math.sin(math.tau*p)) if run else .15+1.80*stress if name=='elbow_bend' else .15
   front=Vector((0,1,0));forward=(front-direction*front.dot(direction)).normalized()
   fore=direction*math.cos(bend)+forward*math.sin(bend)
   if HYBRID:
    old_fore=reference.pose.bones['forearm.'+old_side];fore=(old_fore.tail-old_fore.head).normalized()
   set_world(side+'_Forearm',elbow,fore)
   hand=rig.pose.bones[side+'_Hand'];set_world(hand.name,hand.head.copy(),fore)
  bpy.context.view_layer.update()
  # All 41 bones, including inherited twist bones, are baked for engine playback.
  for p in rig.pose.bones:
   p.keyframe_insert('location',frame=frame+1);p.keyframe_insert('rotation_quaternion',frame=frame+1);p.keyframe_insert('scale',frame=frame+1)
  checks[name].append({'frame':frame+1,'feet':{side:list(rig.pose.bones[side+'_Foot'].head) for side in ['L','R']}})
 track=rig.animation_data.nla_tracks.new();track.name=name;track.strips.new(name,1,action);track.mute=True
rig.animation_data.action=None
for track in rig.animation_data.nla_tracks:track.mute=False
if reference:bpy.data.objects.remove(reference,do_unlink=True)
scene.frame_set(1)
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
for o in meshes:o.select_set(True)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(R/'assets_source/characters/ranger'/('comparison_'+variant+'.blend')))
bpy.ops.export_scene.gltf(filepath=str(R/('Loopbound/assets/characters/ranger/action_comparison/'+variant+'.glb')),export_format='GLB',use_selection=True,export_animation_mode='NLA_TRACKS')
out=R/'local_previews'/variant;out.mkdir(exist_ok=True,parents=True)
(out/'build_checks.json').write_text(json.dumps({'before':before,'after':after,'frames':checks},indent=2))
print('TRIPO BUILD COMPLETE: 41 preserved bones, six actions')
