"""Check symmetric rest joints, loop geometry, joint ranges and planted-foot contact."""
import bpy,json,math,sys,numpy as np
from pathlib import Path
R=Path(__file__).resolve().parents[3]
HYBRID='--hybrid' in sys.argv
variant='tripo_hybrid' if HYBRID else 'tripo_corrected'
bpy.ops.wm.open_mainfile(filepath=str(R/'assets_source/characters/ranger'/('comparison_'+variant+'.blend')))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');scene=bpy.context.scene
assert len(rig.data.bones)==41
mirror=0
for b in rig.data.bones:
 if b.name.startswith('L_'):
  other=rig.data.bones['R_'+b.name[2:]]
  for attr in ['head_local','tail_local']:
   pt=getattr(other,attr).copy();pt.x=-pt.x;mirror=max(mirror,(getattr(b,attr)-pt).length)
assert mirror<1e-6
meshes=[o for o in scene.objects if o.type=='MESH' and o.name.startswith('tripo_part')]
boots={side:min([o for o in meshes if o.name in ['tripo_part_3','tripo_part_5']],key=lambda o:abs(sum(v.co.x for v in o.data.vertices)/len(o.data.vertices)-rig.data.bones[side+'_Foot'].head_local.x)) for side in ['L','R']}
def coords(o):
 ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();a=np.empty(len(m.vertices)*3);m.vertices.foreach_get('co',a);ev.to_mesh_clear();return a.reshape((-1,3))
def angle(a,b):return math.degrees(a.normalized().angle(b.normalized()))
toe_indices={}
for side,boot in boots.items():
 ids=[v.index for v in boot.data.vertices if v.co.z<.10];ys=sorted(boot.data.vertices[i].co.y for i in ids)
 toe_indices[side]=([i for i in ids if boot.data.vertices[i].co.y<ys[len(ys)//5]],[i for i in ids if boot.data.vertices[i].co.y>ys[len(ys)*4//5]])
report={'mirror_error':mirror,'actions':{}}
for track in rig.animation_data.nla_tracks:
 for other in rig.animation_data.nla_tracks:other.mute=other!=track
 strip=track.strips[0];end=round(strip.frame_end);name=track.name;contact=[];knees=[];elbows=[];minfloor=10;maxradius=0;ends=[];toe_yaw=[];knee_outward=[]
 for frame in range(1,end+1):
  scene.frame_set(frame);t=(frame-1)/(end-1)
  for side,offset in [('L',0),('R',.5)]:
   thigh=rig.pose.bones[side+'_Thigh'];calf=rig.pose.bones[side+'_Calf'];upper=rig.pose.bones[side+'_Upperarm'];fore=rig.pose.bones[side+'_Forearm']
   knees.append(angle(thigh.tail-thigh.head,calf.tail-calf.head));elbows.append(angle(upper.tail-upper.head,fore.tail-fore.head))
   vertices=coords(boots[side]);bottom=float(vertices[:,2].min());minfloor=min(minfloor,bottom)
   heel_ids,toe_ids=toe_indices[side];direction=vertices[toe_ids].mean(axis=0)-vertices[heel_ids].mean(axis=0)
   sign=-1 if side=='L' else 1
   toe_yaw.append(math.degrees(math.atan2(sign*direction[0],direction[1])))
   knee_outward.append(sign*(calf.head.x-rig.pose.bones[side+'_Foot'].head.x))
   duty=.5 if HYBRID else .6 if name=='walk' else .42
   if name not in ['walk','run'] or (t+offset)%1<duty:contact.append(abs(bottom))
  if frame in [1,end]:ends.append(np.concatenate([coords(o) for o in meshes]))
  for p in rig.pose.bones:assert all(math.isfinite(v) for v in p.head)
 loop=float(np.max(np.abs(ends[0]-ends[1])))
 result={'support_floor_max_error_m':max(contact),'minimum_floor_z_m':minfloor,'knee_flexion_deg':[min(knees),max(knees)],'elbow_flexion_deg':[min(elbows),max(elbows)],'loop_vertex_delta_m':loop,'toe_outward_yaw_deg':[min(toe_yaw),max(toe_yaw)],'minimum_knee_outward_from_ankle_m':min(knee_outward)}
 report['actions'][name]=result;print(name,result)
 assert loop<.0001,(name,'loop',loop)
 assert max(knees)<155 and min(knees)>=0
 assert max(elbows)<145
 assert max(contact)<.012,(name,'contact',max(contact))
 assert minfloor>-.012,(name,'floor',minfloor)
 if HYBRID:
  assert min(toe_yaw)>0,(name,'inward toes',min(toe_yaw))
  assert min(knee_outward)>-.018,(name,'knee collapse',min(knee_outward))
 # Forward progression during swing, backward foot movement during stance.
 if name in ['walk','run']:
  duty=.5 if HYBRID else .6 if name=='walk' else .42
  ys=[]
  for t in [.1*duty,.8*duty,duty+.15*(1-duty),duty+.8*(1-duty)]:
   scene.frame_set(round(1+t*(end-1)));ys.append(rig.pose.bones['L_Foot'].head.y)
  assert ys[1]<ys[0] and ys[3]>ys[2],(name,ys)
(R/'local_previews'/variant/'verification.json').write_text(json.dumps(report,indent=2))
print('PASS: symmetry, six loops, forward gait, joint ranges, planted feet')
