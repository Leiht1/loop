import bpy
import bmesh
from pathlib import Path
from math import sin, cos, pi, sqrt, exp
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'assets_source/characters/ranger/ranger.blend'
EXPORT = ROOT / 'Loopbound/assets/characters/ranger/ranger.glb'
PREVIEW = ROOT / 'docs/art/ranger'

# Work in a dedicated scene so a user's existing scene is preserved.
if bpy.app.background:
    scene = bpy.context.scene
    scene.name = 'Ranger | Model'
    for startup_object in list(scene.objects):
        bpy.data.objects.remove(startup_object, do_unlink=True)
else:
    scene = bpy.data.scenes.new('Ranger | Model')
    bpy.context.window.scene = scene
scene.unit_settings.system = 'METRIC'
scene.render.fps = 30
scene.frame_start, scene.frame_end = 1, 90
materials = {}

def material(name, hex_color, roughness=.75, metal=0):
    rgb = [int(hex_color[i:i+2], 16)/255 for i in (0, 2, 4)]
    rgba = tuple(c/12.92 if c < .04045 else ((c+.055)/1.055)**2.4 for c in rgb) + (1,)
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = rgba
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = rgba
    shader.inputs['Roughness'].default_value = roughness
    shader.inputs['Metallic'].default_value = metal
    materials[name] = mat

for name, color in {
    'Ivory':'d9c6aa', 'Ivory trim':'aa947b', 'Indigo':'303945',
    'Ink':'262932', 'Teal':'3c5664', 'Teal fold':'4b6671',
    'Wave':'8b9a91', 'Leather':'42322e', 'Leather trim':'795c49',
    'Ochre red':'934932', 'Cord highlight':'ae6347', 'Skin':'d39b7d',
    'Lips':'a4655c', 'Eye white':'e5d3bc', 'Iris':'55362d',
    'Hair':'242025', 'Hair ridge':'31282a', 'Sole':'a7937c',
}.items():
    material(name, color)
material('Bronze','a88157',.46,.55)
material('Jade','83a69a',.31)

rig_data = bpy.data.armatures.new('Ranger skeleton')
rig = bpy.data.objects.new('Ranger', rig_data)
scene.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig
rig.select_set(True)
rig.show_in_front = True
bpy.ops.object.mode_set(mode='EDIT')

def bone(name, head, tail, parent=None):
    b = rig_data.edit_bones.new(name)
    b.head, b.tail = head, tail
    if parent:
        b.parent = rig_data.edit_bones[parent]
    b.use_deform = name != 'root'

bone('root',(0,0,0),(0,0,.15))
bone('pelvis',(0,0,.91),(0,0,1.025),'root')
bone('spine',(0,0,1.025),(0,0,1.18),'pelvis')
bone('chest',(0,0,1.18),(0,0,1.405),'spine')
bone('neck',(0,0,1.405),(0,-.008,1.53),'chest')
bone('head',(0,-.008,1.53),(0,-.002,1.77),'neck')
bone('hair_tie',(0,.082,1.72),(0,.156,1.56),'head')
bone('mantle',(0,.095,1.35),(-.09,.18,1.03),'chest')
bone('mantle_tip',(-.09,.18,1.03),(-.18,.17,.72),'mantle')
for sign, side in [(1,'.L'),(-1,'.R')]:
    def p(x,y,z): return (sign*x,y,z)
    bone('clavicle'+side,p(.035,0,1.372),p(.168,0,1.36),'chest')
    bone('upper_arm'+side,p(.168,0,1.36),p(.273,-.008,1.123),'clavicle'+side)
    bone('forearm'+side,p(.273,-.008,1.123),p(.322,-.039,.917),'upper_arm'+side)
    bone('hand'+side,p(.322,-.039,.917),p(.343,-.053,.829),'forearm'+side)
    bone('fingers'+side,p(.343,-.053,.829),p(.351,-.053,.786),'hand'+side)
    bone('thumb'+side,p(.314,-.063,.875),p(.31,-.081,.827),'hand'+side)
    bone('thigh'+side,p(.094,.005,.92),p(.111,-.026,.523),'pelvis')
    bone('shin'+side,p(.111,-.026,.523),p(.115,.015,.102),'thigh'+side)
    bone('foot'+side,p(.115,.015,.102),p(.119,-.118,.042),'shin'+side)
    bone('toe'+side,p(.119,-.118,.042),p(.119,-.18,.036),'foot'+side)
    bone('skirt'+side,p(.105,0,1.00),p(.145,.008,.68),'pelvis')
bpy.ops.object.mode_set(mode='OBJECT')
meshes = []

def mesh(name, vertices, faces, palette, slots, weights, uv=None):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    for key in palette:
        data.materials.append(materials[key])
    for polygon, slot in zip(data.polygons, slots):
        polygon.material_index = slot
        polygon.use_smooth = True
    bm = bmesh.new()
    bm.from_mesh(data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(data)
    bm.free()
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.parent = rig
    if uv:
        layer = data.uv_layers.new(name='UVMap')
        for poly in data.polygons:
            indices = [data.loops[i].vertex_index for i in poly.loop_indices]
            seam = max(uv[i][0] for i in indices)-min(uv[i][0] for i in indices) > .75
            for loop in poly.loop_indices:
                u,v = uv[data.loops[loop].vertex_index]
                layer.data[loop].uv = (u+1 if seam and u<.25 else u,v)
    groups = {}
    for i, vertex in enumerate(vertices):
        w = {weights:1} if isinstance(weights,str) else weights(vertex)
        for key, value in w.items():
            if value <= 0: continue
            if key not in groups:
                groups[key] = obj.vertex_groups.new(name=key)
            groups[key].add([i], value, 'REPLACE')
    mod = obj.modifiers.new('Ranger skin','ARMATURE')
    mod.object = rig
    meshes.append(obj)
    return obj

def blend(a,b,t):
    t = min(1,max(0,t))
    t = t*t*(3-2*t)
    return {a:1-t,b:t}

def rings(name, rows, palette, weights, n=32, slot=None, deform=None, caps=True):
    vs, uv, faces, slots = [], [], [], []
    for j,(x,y,z,rx,ry) in enumerate(rows):
        for i in range(n):
            a=2*pi*i/n
            v=(x+rx*sin(a),y-ry*cos(a),z)
            vs.append(deform(v,a,j) if deform else v)
            uv.append((i/n,j/(len(rows)-1)))
    for j in range(len(rows)-1):
        for i in range(n):
            k=(i+1)%n
            faces.append((j*n+i,j*n+k,(j+1)*n+k,(j+1)*n+i))
            slots.append(slot(j,i) if slot else 0)
    if caps:
        faces.extend([tuple(reversed(range(n))),tuple(range(len(vs)-n,len(vs)))])
        slots.extend([0,0])
    return mesh(name,vs,faces,palette,slots,weights,uv)

def tube(name, points, key, weights, segments=9, flatten=1.0):
    vs, faces, uv = [], [], []
    for i,(x,y,z,r) in enumerate(points):
        start=Vector(points[max(0,i-1)][:3])
        end=Vector(points[min(len(points)-1,i+1)][:3])
        tangent=(end-start).normalized()
        axis=tangent.cross(Vector((0,1,0)))
        if axis.length < .01:
            axis=tangent.cross(Vector((1,0,0)))
        axis.normalize()
        normal=tangent.cross(axis)
        for j in range(segments):
            a=2*pi*j/segments
            vs.append(tuple(Vector((x,y,z))+r*(axis*cos(a)+normal*sin(a)*flatten)))
            uv.append((j/segments,i/(len(points)-1)))
    for i in range(len(points)-1):
        for j in range(segments):
            a=i*segments+j
            b=i*segments+(j+1)%segments
            faces.append((a,b,b+segments,a+segments))
    faces += [tuple(reversed(range(segments))),tuple(range(len(vs)-segments,len(vs)))]
    return mesh(name,vs,faces,[key],[0]*len(faces),weights,uv)

def orb(name, center, scale, key, weights, n=24, levels=12):
    x,y,z=center
    a,b,c=scale
    return rings(name,[(x,y,z+c*sin(t),a*cos(t),b*cos(t))
        for t in [(-.499+i*.998/levels)*pi for i in range(levels+1)]],[key],weights,n)

def torso_weight(v):
    z=v[2]
    return blend('pelvis','spine',(z-.96)/.15) if z<1.11 else blend('spine','chest',(z-1.11)/.18)

torso=[(0,.006,.946,.151,.096),(0,.003,.977,.151,.099),(0,0,1.035,.143,.101),
       (0,0,1.105,.148,.103),(0,.002,1.178,.169,.115),(0,.009,1.249,.186,.113),
       (0,.012,1.305,.184,.101),(0,.01,1.353,.170,.078),(0,.008,1.381,.119,.068),
       (0,.006,1.399,.068,.058),(0,.002,1.429,.053,.05)]
rings('Wrap jacket',torso,['Ivory'],torso_weight,48,
      deform=lambda v,a,j:(v[0],v[1]+.004*sin(7*a+j*.44)*sin(pi*j/10),v[2]))
rings('Inner standing collar',[(0,.001,1.397,.062,.052),(0,0,1.471,.057,.051),
      (0,-.002,1.494,.056,.050),(0,-.002,1.500,.057,.051)],
      ['Ink','Indigo'],'neck',40,lambda j,i:int(j==2),caps=False)
rings('Neck',[(0,0,1.412,.052,.043),(0,-.001,1.463,.046,.043),
      (0,-.007,1.518,.052,.05),(0,-.008,1.552,.058,.055)],['Skin'],
      lambda v:blend('neck','head',(v[2]-1.49)/.055))

def face_shape(v,a,j):
    x,y,z=v
    front=max(0,cos(a))**7
    # Shape the nose bridge, sockets, cheek planes and mouth directly in the head mesh.
    g=lambda cx,cz,sx,sz: exp(-((abs(x)-cx)/sx)**2-((z-cz)/sz)**2)
    y+=front*(.015*g(.033,1.658,.018,.012)-.010*g(0,1.636,.018,.026)
              -.017*g(0,1.621,.015,.013)-.010*g(.038,1.636,.023,.018)
              -.006*g(0,1.586,.027,.012))
    return x,y,z

profile=[(1.539,-.030,.021,.028),(1.545,-.024,.040,.044),(1.554,-.013,.052,.061),
    (1.566,-.003,.062,.069),(1.579,.001,.069,.072),(1.593,.003,.073,.075),
    (1.607,.005,.078,.078),(1.620,.006,.080,.079),(1.631,.007,.083,.078),
    (1.642,.008,.083,.078),(1.653,.009,.082,.079),(1.665,.011,.081,.078),
    (1.676,.014,.080,.075),(1.689,.015,.079,.071),(1.707,.015,.075,.066),
    (1.725,.016,.065,.057),(1.744,.015,.042,.038),(1.752,.013,.009,.010)]
rings('Face and cranium',[(0,y,z,rx,ry) for z,y,rx,ry in profile],['Skin'],'head',96,deform=face_shape)
for sign in (1,-1):
    orb('Ear',(sign*.077,.002,1.615),(.014,.018,.027),'Skin','head')
    orb('Ear concha',(sign*.083,-.013,1.617),(.007,.004,.014),'Lips','head')
    eye=(sign*.032,-.063,1.654)
    orb('Almond eye',eye,(.020,.008,.007),'Eye white','head')
    orb('Iris',(sign*.031,-.071,1.654),(.008,.0036,.007),'Iris','head')
    orb('Pupil',(sign*.031,-.0742,1.654),(.0034,.0015,.0044),'Hair','head',16,8)
    orb('Eye catchlight',(sign*.028,-.0754,1.657),(.0016,.0006,.0016),'Eye white','head',12,6)
    tube('Upper lash',[(sign*x,y,z,r) for x,y,z,r in [
        (.012,-.066,1.654,.0009),(.024,-.071,1.660,.0018),(.038,-.070,1.661,.0018),
        (.050,-.063,1.656,.001)]],'Hair','head')
    tube('Tapered brow',[(sign*x,y,z,r) for x,y,z,r in [
        (.012,-.071,1.671,.001),(.023,-.072,1.674,.0032),(.039,-.068,1.675,.0029),
        (.055,-.056,1.669,.0008)]],'Hair','head')
    orb('Nostril',(sign*.009,-.086,1.614),(.003,.0016,.0015),'Lips','head',16,8)
tube('Mouth seam',[(-.018,-.071,1.585,.001),(-.009,-.077,1.587,.0015),
    (0,-.079,1.586,.0013),(.010,-.077,1.587,.0013),(.018,-.071,1.586,.0008)],'Lips','head')

# Each hair lock is a tapered ribbon volume, laid over a fitted scalp.
rings('Hair cap',[(0,.022,1.649,.086,.079),(0,.019,1.681,.091,.083),
    (0,.018,1.714,.092,.086),(0,.021,1.747,.078,.073),(0,.025,1.768,.045,.046),
    (0,.025,1.776,.006,.011)],['Hair','Hair ridge'],'head',48,
    lambda j,i: 0,
    lambda v,a,j:(v[0],v[1],v[2]-.075*max(0,-cos(a))*(1-j/5)**2))
for i in range(13):
    a=-1.55+3.1*i/12
    x=sin(a)
    drop=.027+.066*abs(x)+.014*sin(i*2.4)
    tube('Swept fringe %02d'%i,[(.041*x,.002,1.758+.008*sin(i),.017),
        (.071*x-.017,-.043,1.744,.021),(.092*x-.013,-.068+.022*x*x,1.710,.017),
        (.092*x+.008,-.076+.036*x*x,1.707-drop*.72,.011),
        (.095*x+.018,-.062+.044*x*x,1.707-drop,.0009)],
        'Hair ridge' if i in (4,9) else 'Hair','head',12,.56)
for i in range(3):
    tube('Loose crown lock',[(.026+.014*i,.013,1.751,.010),
         (.023+.018*i,.009,1.771,.008),(.005+.019*i,-.004,1.785-.004*i,.0035),
         (-.014+.018*i,-.016,1.776,.0005)],'Hair','head',10,.63)
for i in range(11):
    a=1.17+4.0*i/10
    x,y=sin(a),-cos(a)
    tube('Nape lock %02d'%i,[(x*.055,.024+y*.047,1.751,.014),
        (x*.086,.028+y*.069,1.703,.017),(x*.087,.034+y*.077,1.652,.015),
        (x*.083,.035+y*.069,1.586+.018*sin(i*2),.001)],
        'Hair ridge' if i%4==0 else 'Hair','head',11,.55)
for i in range(7):
    a=i*2*pi/7
    x=cos(a)*.018
    tube('Tied hair %02d'%i,[(x,.086+sin(a)*.012,1.731,.017),
        (x*1.3,.113,1.739+sin(a)*.015,.016),(x*1.7,.139,1.704+sin(a)*.018,.014),
        (x*2+.019,.155,1.651+sin(a)*.025,.001)],'Hair' if i%3 else 'Hair ridge','hair_tie',11,.68)
tube('Rust hair binding',[(-.024,.099,1.732,.008),(-.01,.108,1.746,.008),
    (.012,.106,1.745,.008),(.024,.098,1.73,.007)],'Ochre red','hair_tie')
for side in (-1,1):
    tube('Hair ribbon',[(.018*side,.101,1.733,.008),(.026*side,.122,1.699,.010),
        (.037*side,.145,1.649,.009),(.047*side,.161,1.596+.017*side,.001)],
        'Ochre red','hair_tie',8,.23)

def sash(name, rows, start, end, palette, weights, n=26, waves=False):
    vs, uv, faces, slots = [], [], [], []
    for j,(z,rx,ry,twist,hem) in enumerate(rows):
        v=j/(len(rows)-1)
        for i in range(n+1):
            u=i/n
            a=start+(end-start)*u+twist
            fold=.008*sin(10*a+2*v)*sin(pi*v*.75)
            vs.append(((rx+fold)*sin(a),-(ry+fold)*cos(a),z+hem*u))
            uv.append((u,v))
    for j in range(len(rows)-1):
        for i in range(n):
            a=j*(n+1)+i
            faces.append((a,a+1,a+n+2,a+n+1))
            slots.append(1 if j==len(rows)-2 or i in (0,n-1) else 0)
    obj=mesh(name,vs,faces,palette,slots,weights,uv)
    bpy.context.view_layer.objects.active=obj
    solid=obj.modifiers.new('Turned cloth edge','SOLIDIFY')
    solid.thickness=.005
    bpy.ops.object.modifier_apply(modifier=solid.name)

sash('Overlapped ivory skirt',[(1.033,.153,.109,0,0),(.963,.170,.118,-.04,0),
     (.88,.186,.122,-.08,.015),(.79,.202,.131,-.10,.035),(.69,.207,.137,-.14,.055),
     (.682,.207,.138,-.14,.055)],-.19,3.61,['Ivory','Ivory trim','Wave'],
     lambda v:blend('pelvis','skirt.L',(1.01-v[2])/.23))
sash('Crossed indigo overskirt',[(1.037,.157,.117,0,0),(.973,.178,.127,.04,0),
     (.889,.187,.140,.08,.020),(.791,.194,.153,.13,.040),(.692,.202,.164,.17,.075),
     (.682,.204,.164,.17,.075)],-3.58,.35,['Indigo','Teal','Wave'],
     lambda v:blend('pelvis','skirt.R',(1.01-v[2])/.23),waves=True)
rings('Layered waist sash',[(0,.001,.964,.169,.119),(0,.002,.983,.169,.120),
      (0,.002,1.006,.160,.117),(0,.003,1.033,.153,.111),(0,.003,1.060,.153,.109)],
      ['Ink','Indigo','Leather trim'],'pelvis',48,lambda j,i:[1,0,1,0][j])
for layer in range(2):
    tube('Wrapped rust waist cord',[(.170*sin(a),-.123*cos(a),.994+layer*.012+.009*sin(a+.9),.0055)
        for a in [2*pi*i/64 for i in range(65)]],'Ochre red' if layer==0 else 'Cord highlight','pelvis',8)
for sign in (-1,1):
    tube('Rust cord knot',[(.043,-.129,1.002,.008),(.043+sign*.025,-.141,1.016,.008),
        (.043+sign*.035,-.145,.997,.007),(.042,-.134,.997,.006)],'Ochre red','pelvis')
    tube('Rust cord tail',[(.043,-.139,1.003,.007),(.043+sign*.014,-.145,.961,.008),
        (.043+sign*.020,-.151,.903+.025*sign,.007),(.048+sign*.018,-.150,.891+.025*sign,.002)],
        'Ochre red','pelvis',9,.60)

def loop(name, center, radius, thickness, key, weights):
    x,y,z=center
    vs, faces, uv=[],[],[]
    for i in range(32):
        a=i*2*pi/32
        for j in range(10):
            b=j*2*pi/10
            r=radius+thickness*cos(b)
            vs.append((x+r*cos(a),y+thickness*sin(b),z+r*sin(a)))
            uv.append((i/32,j/10))
    for i in range(32):
        for j in range(10):
            a=i*10
            b=((i+1)%32)*10
            k=(j+1)%10
            faces.append((a+j,b+j,b+k,a+k))
    mesh(name,vs,faces,[key],[0]*len(faces),weights,uv)

loop('Jade waist ring',(.112,-.113,.892),.020,.0045,'Jade','pelvis')
tube('Jade ring tie',[(.108,-.120,.984,.003),(.107,-.129,.951,.003),(.112,-.116,.912,.003)],
     'Ochre red','pelvis')
tube('Leather shoulder strap',[(-.129,-.070,1.354,.022),(-.103,-.112,1.287,.022),
     (-.069,-.118,1.224,.022),(-.028,-.114,1.159,.021),(.014,-.111,1.09,.020),
     (.045,-.109,1.035,.019)],'Leather',torso_weight,8,.26)
loop('Bronze strap ring',(-.101,-.123,1.289),.018,.0044,'Bronze','chest')
tube('Diagonal wrap edge',[(.098,-.072,1.371,.012),(.081,-.107,1.318,.012),
     (.051,-.115,1.266,.012),(.015,-.119,1.208,.011),(-.019,-.108,1.157,.010),
     (-.059,-.095,1.105,.009),(-.097,-.084,1.044,.008)],'Ivory trim',torso_weight,9,.30)

rings('Folded blue shoulder scarf',[(0,.018,1.351,.130,.106),(0,.021,1.365,.175,.116),
    (0,.018,1.391,.175,.112),(0,.014,1.416,.141,.107),(0,.008,1.438,.108,.090),
    (0,.005,1.463,.074,.065),(0,.009,1.470,.058,.052)],
    ['Teal'],'chest',64,deform=
    lambda v,a,j:(v[0],v[1]+.006*sin(4*a+j*.6),v[2]-.055*cos(a)*sin(pi*j/6)+.016*sin(a+.7)))

def mantle_weight(v):
    z=v[2]
    return blend('mantle','chest',(z-1.20)/.16) if z>1.17 else blend('mantle_tip','mantle',(z-.76)/.31)

def mantle_surface(u,t):
    return (-.02-.11*t+(u-.5)*(.286-.125*t),
        .114+.093*sin(t*pi*.63)+.014*cos(u*pi*4.4+.9*t)-.018*abs(2*u-1),
        1.408-.60*t+.15*u*t**2-.04*sin(pi*u)*(1-t))

vs, uv, faces, slots = [], [], [], []
for j in range(21):
    t=j/20
    for i in range(23):
        u=i/22
        vs.append(mantle_surface(u,t))
        uv.append((u,t))
for j in range(20):
    for i in range(22):
        a=j*23+i
        faces.append((a,a+1,a+24,a+23))
        slots.append(1 if i in (0,21) or j==19 else 0)
cape=mesh('Asymmetric woven mantle',vs,faces,['Teal','Teal fold','Wave'],slots,mantle_weight,uv)
bpy.context.view_layer.objects.active=cape
solid=cape.modifiers.new('Woven thickness','SOLIDIFY')
solid.thickness=.006
bpy.ops.object.modifier_apply(modifier=solid.name)
for crest in range(3):
    points=[]
    for i in range(30):
        t=i/29
        angle=-1.5+4.5*t
        u=.18+.22*crest+.15*cos(angle)*(1-t*.5)
        depth=.88+.050*sin(angle)*(1-t*.45)-.055*t
        x,y,z=mantle_surface(u,depth)
        points.append((x,y+.0045,z,.0007+.0022*sin(pi*t)**.65))
    tube('Embroidered wave',points,'Wave',mantle_weight,7,.45)

for sign, side in [(1,'.L'),(-1,'.R')]:
    def p(x,y,z,rx,ry): return (sign*x,y,z,rx,ry)
    def sleeve_weight(v):
        z=v[2]
        if z>1.31:
            return blend('upper_arm'+side,'clavicle'+side,(z-1.31)/.075)
        return blend('forearm'+side,'upper_arm'+side,(z-1.09)/.087)
    def folds(v,a,j):
        s=.005*sin(6*a+j*.65)
        return v[0]+s*sin(a),v[1]-s*cos(a),v[2]
    rings('Wide ivory sleeve'+side,[p(.152,.008,1.368,.057,.066),p(.176,.004,1.332,.076,.088),
         p(.211,0,1.278,.080,.087),p(.236,-.004,1.218,.082,.088),
         p(.258,-.012,1.181,.088,.095),p(.261,-.012,1.169,.087,.093)],
         ['Ivory','Ivory trim','Wave'],sleeve_weight,40,
         lambda j,i:1 if j==4 else (2 if j==3 and i in range(7,14) and (i+sign)%4!=0 else 0),folds)
    rings('Gathered inner sleeve'+side,[p(.183,.004,1.333,.065,.077),p(.219,0,1.259,.068,.070),
         p(.255,-.008,1.192,.066,.062),p(.273,-.009,1.148,.062,.064),
         p(.283,-.014,1.106,.057,.055),p(.286,-.018,1.075,.043,.042),
         p(.289,-.021,1.061,.040,.040)],['Ink','Indigo'],sleeve_weight,32,
         lambda j,i: int(j==5),folds)
    rings('Forearm'+side,[p(.283,-.017,1.082,.025,.026),p(.294,-.025,1.049,.035,.032),
         p(.306,-.031,.987,.033,.029),p(.322,-.039,.917,.024,.022)],['Skin'],'forearm'+side)
    rings('Wrapped leather guard'+side,[p(.306,-.03,1.002,.038,.034),p(.311,-.031,.982,.038,.033),
         p(.317,-.036,.955,.034,.031),p(.322,-.038,.929,.030,.027),p(.322,-.039,.922,.029,.027)],
         ['Leather','Leather trim'],'forearm'+side,32,lambda j,i: int(j in (0,3)))
    for direction in (-1,1):
        tube('Wrist wrap'+side,[(sign*(.313+.036*sin(a)),-.034-.033*cos(a),
            .958+direction*.012*sin(a),.0028) for a in [i*2*pi/28 for i in range(29)]],
            'Leather trim','forearm'+side,7)
    rings('Palm'+side,[p(.322,-.039,.928,.023,.022),p(.327,-.046,.901,.026,.021),
         p(.336,-.047,.877,.028,.022),p(.343,-.046,.850,.025,.017),
         p(.346,-.046,.839,.020,.014)],['Skin'],'hand'+side,28)
    for i in range(4):
        y=-.063+i*.012
        x=.330+i*.007
        z=.842+(.005 if i==3 else 0)
        tube('Finger %d'%i+side,[(sign*x,y,z,.008),(sign*(x+.009),y-.001,z-.017,.0075),
            (sign*(x+.004),y-.004,z-.032+(i-1)**2*.003,.006),
            (sign*(x-.001),y-.005,z-.035+(i-1)**2*.003,.0034)],
            'Skin',lambda v:blend('fingers'+side,'hand'+side,(v[2]-.815)/.03),9)
    tube('Thumb'+side,[(sign*.315,-.059,.893,.011),(sign*.307,-.072,.873,.010),
        (sign*.309,-.077,.853,.008),(sign*.318,-.080,.841,.004)],'Skin','thumb'+side,10)

    def pants_weight(v):
        z=v[2]
        return blend('thigh'+side,'pelvis',(z-.85)/.12) if z>.75 else blend('shin'+side,'thigh'+side,(z-.46)/.135)
    rings('Pleated travel trousers'+side,[p(.088,.006,.979,.073,.091),p(.093,.004,.928,.091,.096),
        p(.105,.005,.860,.102,.100),p(.116,.005,.770,.108,.101),p(.123,.004,.666,.106,.091),
        p(.128,-.008,.574,.103,.081),p(.128,-.019,.519,.097,.075),p(.129,-.013,.455,.083,.068),
        p(.128,-.001,.390,.073,.061),p(.126,.004,.355,.050,.051),p(.126,.005,.332,.048,.049)],
        ['Ink'],pants_weight,40,deform=folds)
    rings('Cloth gaiter'+side,[p(.126,.004,.369,.058,.058),p(.124,.008,.340,.056,.054),
        p(.122,.012,.291,.051,.048),p(.120,.017,.230,.047,.044),p(.117,.017,.171,.042,.043),
        p(.116,.016,.143,.041,.041)],['Leather','Leather trim'],'shin'+side,32,lambda j,i:int(j==0))
    for direction in (-1,1):
        tube('Crossed gaiter ties'+side,[(sign*(.121+(.050-.009*t)*sin(a)),
            .014-(.050-.008*t)*cos(a),.334-.184*t,.0034)
            for t,a in [(i/54,direction*i*5*pi/54) for i in range(55)]],'Leather trim','shin'+side,7)
    rings('Soft leather boot'+side,[p(.118,-.045,.001,.053,.107),p(.118,-.049,.009,.058,.115),
        p(.118,-.049,.025,.057,.114),p(.118,-.046,.039,.055,.113),p(.118,-.039,.054,.052,.102),
        p(.118,-.020,.071,.052,.081),p(.117,.007,.098,.052,.055),p(.116,.015,.129,.048,.048),
        p(.116,.017,.165,.047,.047)],['Leather','Sole','Leather trim'],
        lambda v:blend('foot'+side,'shin'+side,(v[2]-.094)/.069),40,
        lambda j,i:1 if j<2 else (2 if j==2 else 0),
        lambda v,a,j:(v[0]+sign*.010*max(0,cos(a))*(1-j/8),v[1],v[2]))
    for i in range(2):
        tube('Boot tie'+side,[(sign*.078,-.087+.018*i,.060+.012*i,.0028),
            (sign*.119,-.111+.018*i,.070+.012*i,.0033),
            (sign*.158,-.085+.018*i,.062+.012*i,.0028)],'Leather trim','foot'+side)

from mathutils import Matrix, Quaternion

def swing(name, axis, angle):
    pose=rig.pose.bones[name]
    local_axis=pose.bone.matrix_local.to_3x3().inverted() @ Vector(axis)
    pose.rotation_quaternion=Quaternion(local_axis,angle) @ pose.rotation_quaternion

def orient_bone(pose, head, tail):
    base=(pose.parent.matrix @ pose.parent.bone.matrix_local.inverted()
          @ pose.bone.matrix_local if pose.parent else pose.bone.matrix_local.copy())
    axis=base.to_3x3().col[1].normalized()
    q=axis.rotation_difference((tail-head).normalized())
    pose.matrix=Matrix.Translation(head) @ q.to_matrix().to_4x4() @ base.to_3x3().to_4x4()
    bpy.context.view_layer.update()

def plant_leg(side, y, lift, pitch):
    upper=rig.pose.bones['thigh'+side]
    lower=rig.pose.bones['shin'+side]
    foot=rig.pose.bones['foot'+side]
    hip=upper.head.copy()
    ankle=foot.bone.head_local.copy()
    ankle.y+=y
    ankle.z+=lift
    axis=ankle-hip
    a,b=upper.bone.length,lower.bone.length
    d=min(a+b-.0004,max(.02,axis.length))
    axis.normalize()
    ankle=hip+axis*d
    projection=(a*a+d*d-b*b)/(2*d)
    pole=Vector((0,-1,0))
    pole=(pole-axis*pole.dot(axis)).normalized()
    knee=hip+axis*projection+pole*sqrt(max(0,a*a-projection*projection))
    orient_bone(upper,hip,knee)
    orient_bone(lower,knee,ankle)
    foot.matrix=Matrix.Translation(ankle) @ Matrix.Rotation(pitch,4,'X') @ foot.bone.matrix_local.to_3x3().to_4x4()
    bpy.context.view_layer.update()

def motion(name, duration, speed):
    rig.animation_data_create()
    anim=rig.animation_data
    action=bpy.data.actions.new(name)
    action.use_fake_user=True
    anim.action=action
    steps=round(duration*30)
    duration=steps/30
    running=name=='run'
    stance=.40 if running else .56
    travel=speed*duration*stance
    for i in range(steps+1):
        t=(i%steps)/steps
        frame=i+1
        for p in rig.pose.bones:
            p.rotation_mode='QUATERNION'
            p.matrix_basis=Matrix.Identity(4)
        pulse=2*pi*t
        pelvis=rig.pose.bones['pelvis']
        bob=(-.062+.036*cos(pulse*2) if running else
             -.035-.017*cos(pulse*2) if speed else -.017+.0025*cos(pulse))
        pelvis.location=pelvis.bone.matrix_local.to_3x3().inverted() @ Vector((.011*sin(pulse) if speed else 0,0,bob))
        swing('pelvis',(0,0,1),(.10 if running else .055)*cos(pulse) if speed else .016*sin(pulse))
        swing('chest',(0,0,1),(-.18 if running else -.085)*cos(pulse) if speed else .016*sin(pulse))
        swing('spine',(1,0,0),(.16 if running else .055) if speed else .014*sin(pulse))
        swing('head',(1,0,0),(-.10 if running else -.025) if speed else .015*sin(pulse+.3))
        swing('head',(0,0,1),.028*sin(pulse+.3))
        swing('mantle',(1,0,0),(.22 if running else .07) + .045*sin(pulse-.8) if speed else .025*sin(pulse))
        swing('mantle_tip',(1,0,0),.09*sin(pulse-1.1) if speed else .025*sin(pulse-1.1))
        swing('hair_tie',(1,0,0),.065*sin(pulse-.7) if speed else .02*sin(pulse))
        for sign,side in ((1,'.L'),(-1,'.R')):
            cycle=(t+(0 if sign==1 else .5))%1
            counter=cos(2*pi*cycle)
            swing('upper_arm'+side,(0,1,0),sign*(.24 if running else .20))
            swing('upper_arm'+side,(1,0,0),-(.67 if running else .30)*counter if speed else -.035+.018*sign*sin(pulse))
            swing('forearm'+side,(1,0,0),-(.88+.22*counter if running else .23+.15*counter) if speed else -.075)
            swing('fingers'+side,(1,0,0),-.23 if running else -.10)
            swing('skirt'+side,(1,0,0),(.30 if running else .23)*counter+.02 if speed else 0)
            bpy.context.view_layer.update()
            if speed and cycle<stance:
                y=travel*(cycle/stance-.5)
                lift,pitch=0,0
            elif speed:
                air=(cycle-stance)/(1-stance)
                y=travel*(.5-(.5-.5*cos(pi*air)))
                lift=(.36 if running else .125)*sin(pi*air)**1.2
                pitch=(.62 if running else .33)*sin(2*pi*air)
            else:
                y,lift,pitch=sign*.023,0,0
            plant_leg(side,y,lift,pitch)
        for p in rig.pose.bones:
            if p.name!='root':
                p.keyframe_insert('rotation_quaternion',frame=frame,group=p.name)
                if p.name=='pelvis' or p.name.startswith(('thigh','shin','foot')):
                    p.keyframe_insert('location',frame=frame,group=p.name)
    anim.action=None
    track=anim.nla_tracks.new()
    track.name=name
    strip=track.strips.new(name,1,action)
    track.mute=name!='idle'
    return action

motion('idle',3.0,0)
motion('walk',.60,2.6)
motion('run',.59,6.0)
rig.rotation_euler.z=pi  # Blender +Y becomes Godot -Z.
scene.frame_set(1)

def aim(obj,target):
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()

studio=bpy.data.collections.new('Studio | preview only')
scene.collection.children.link(studio)
def add_studio(name,data,location,target):
    ob=bpy.data.objects.new(name,data)
    studio.objects.link(ob)
    ob.location=location
    aim(ob,target)
    return ob

cam_data=bpy.data.cameras.new('Orthographic studio')
cam_data.type='ORTHO'
cam_data.ortho_scale=2.02
cam=add_studio('Orthographic studio',cam_data,(0,5,.89),(0,0,.89))
scene.camera=cam
for name,location,power,size,color in [
    ('Key',(2,3,3.2),330,3.0,(1,.86,.72)),
    ('Fill',(-2,2,1.8),200,3.0,(.74,.85,1)),
    ('Rim',(0,-2,3.0),380,2.5,(.82,.89,1)),
]:
    data=bpy.data.lights.new(name,'AREA')
    data.energy,data.shape,data.size,data.color=power,'DISK',size,color
    add_studio(name,data,location,(0,0,1))
scene.world=bpy.data.worlds.new('Studio slate')
scene.world.use_nodes=True
bg=scene.world.node_tree.nodes.get('Background')
bg.inputs['Color'].default_value=(.17,.21,.25,1)
bg.inputs['Strength'].default_value=.29
scene.render.engine='CYCLES'
scene.cycles.device='CPU'
scene.cycles.samples=12
scene.cycles.use_denoising=True
scene.render.threads_mode='FIXED'
scene.render.threads=8
scene.render.resolution_x=620
scene.render.resolution_y=920
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.render.film_transparent=True
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.region_3d.view_location=(0,0,.91)
            area.spaces.active.region_3d.view_distance=2.65
            area.spaces.active.region_3d.view_rotation=Quaternion((.14,.08,.69,.70)).normalized()
            area.spaces.active.shading.color_type='MATERIAL'

bpy.ops.object.select_all(action='DESELECT')
rig.select_set(True)
bpy.context.view_layer.objects.active=rig
scene['Asset purpose']='Loopbound ranger | editable weighted clothing, anatomy, hair and locomotion'
old_save_versions=bpy.context.preferences.filepaths.save_version
bpy.context.preferences.filepaths.save_version=0
try:
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE))
finally:
    bpy.context.preferences.filepaths.save_version=old_save_versions

# Combine only the export meshes to keep the editable source parts separate.
copies=[]
for original in meshes:
    copy=original.copy()
    copy.data=original.data.copy()
    scene.collection.objects.link(copy)
    copy.select_set(True)
    copies.append(copy)
rig.select_set(False)
bpy.context.view_layer.objects.active=copies[0]
bpy.ops.object.join()
game_mesh=bpy.context.object
game_mesh.name='RangerMesh'
rig.select_set(True)
bpy.context.view_layer.objects.active=rig
for track in rig.animation_data.nla_tracks:
    track.mute=False
bpy.ops.export_scene.gltf(filepath=str(EXPORT),export_format='GLB',use_selection=True,
    export_animation_mode='NLA_TRACKS',export_yup=True,export_cameras=False,
    export_lights=False,export_apply=False,export_force_sampling=True)
bpy.data.objects.remove(game_mesh,do_unlink=True)
for track in rig.animation_data.nla_tracks:
    track.mute=track.name!='idle'
scene.frame_set(1)

def preview():
    for name,location in [('front',(0,5,.89)),('side',(5,0,.89)),('back',(0,-5,.89))]:
        cam.location=location
        aim(cam,(0,0,.89))
        scene.render.filepath=str(PREVIEW/(name+'.png'))
        bpy.ops.render.render(write_still=True,scene=scene.name)
    (PREVIEW/'blender_done.tmp').write_text('Saved source, exported GLB, rendered orthographic views.')
    return None
if bpy.app.background:
    preview()
else:
    bpy.app.timers.register(preview,first_interval=.5)
