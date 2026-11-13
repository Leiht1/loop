"""Build two character variants and six shared in-place diagnostic actions.
Original GLB input is preserved. Component rules refer to this fixed source asset.
"""
import bpy, math, time, json
from pathlib import Path
from mathutils import Vector, Quaternion, Matrix
ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'Loopbound/assets/characters/ranger/action_comparison'
OUT.mkdir(parents=True, exist_ok=True)
report = []
for variant, filename, arm_drop in [('topology', '主角网格拓扑.glb', 1.0), ('triangles', '主角骨骼.glb', 0.0)]:
    started = time.monotonic()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    data = bpy.data.armatures.new('Rig')
    rig = bpy.data.objects.new('Rig', data)
    bpy.context.collection.objects.link(rig)
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(ROOT / 'assets_source/characters/ranger/animation_inputs' / filename))
    meshes = [o for o in bpy.context.scene.objects if o not in before and o.type == 'MESH']
    if variant == 'topology':
        import bmesh
        for obj in meshes:
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            bmesh.ops.delete(bm, geom=[v for v in bm.verts if abs((obj.matrix_world @ v.co).y) > 0.15], context='VERTS')
            bm.to_mesh(obj.data)
            bm.free()
    if variant == 'triangles':
        rotation = Matrix.Rotation(math.pi / 2, 4, 'Z')
        for obj in meshes:
            obj.matrix_world = rotation @ obj.matrix_world
    coords = [o.matrix_world @ v.co for o in meshes for v in o.data.vertices]
    lo = Vector(tuple((min((v[i] for v in coords)) for i in range(3))))
    hi = Vector(tuple((max((v[i] for v in coords)) for i in range(3))))
    scale = 1.8 / (hi.z - lo.z)
    center = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))
    for o in meshes:
        world = o.matrix_world.copy()
        for v in o.data.vertices:
            v.co = (world @ v.co - center) * scale
        o.parent = None
        o.matrix_world.identity()
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')

    def add_bone(name, head, tail, parent=None):
        bone = rig.data.edit_bones.new(name)
        bone.head = head
        bone.tail = tail
        if parent:
            bone.parent = rig.data.edit_bones[parent]
    add_bone('root', (0, 0, 0), (0, 0, 0.1))
    add_bone('pelvis', (0, 0, 0.92), (0, 0, 1.05), 'root')
    add_bone('spine', (0, 0, 1.05), (0, 0, 1.25), 'pelvis')
    add_bone('chest', (0, 0, 1.25), (0, 0, 1.45), 'spine')
    add_bone('neck', (0, 0, 1.45), (0, 0, 1.56), 'chest')
    add_bone('head', (0, 0, 1.56), (0, 0, 1.8), 'neck')
    for side, sign in [('L', 1), ('R', -1)]:
        points = [(sign * 0.17, 0, 1.40), (sign * 0.215, 0, 1.17), (sign * 0.225, 0.015, 0.94), (sign * 0.225, 0.015, 0.8)]
        if variant == 'triangles':
            points = [(sign * 0.20, 0, 1.34), (sign * 0.53, 0, 1.34), (sign * 0.83, 0, 1.34), (sign * 0.95, 0, 1.34)]
        for i, name in enumerate(['upper_arm', 'forearm', 'hand']):
            add_bone(name + '.' + side, points[i], points[i + 1], 'chest' if i == 0 else ['upper_arm', 'forearm'][i - 1] + '.' + side)
        add_bone('thigh.' + side, (sign * 0.12, 0, 0.93), (sign * 0.12, 0, 0.5), 'pelvis')
        add_bone('shin.' + side, (sign * 0.12, 0, 0.5), (sign * 0.12, 0, 0.12), 'thigh.' + side)
        add_bone('foot.' + side, (sign * 0.12, 0, 0.12), (sign * 0.12, 0.16, 0.06), 'shin.' + side)
    bpy.ops.object.mode_set(mode='OBJECT')

    def smooth(a, b, value):
        t = max(0, min(1, (value - a) / (b - a)))
        return t * t * (3 - 2 * t)
    for obj in meshes:
        obj.data.validate(verbose=True)
        adjacency = [[] for _ in obj.data.vertices]
        for edge in obj.data.edges:
            a, b = edge.vertices
            adjacency[a].append(b)
            adjacency[b].append(a)
        component_of = {}
        visited = set()
        for vertex in obj.data.vertices:
            if vertex.index in visited:
                continue
            stack = [vertex.index]
            component = []
            visited.add(vertex.index)
            while stack:
                current = stack.pop()
                component.append(current)
                for other in adjacency[current]:
                    if other not in visited:
                        visited.add(other)
                        stack.append(other)
            center = sum((obj.data.vertices[i].co for i in component), Vector()) / len(component)
            kind = 'body'
            if len(component) in [149, 150]:
                kind = 'arm'
            elif len(component) == 304:
                kind = 'cape_head'
            elif center.z > 1.55:
                kind = 'head'
            elif center.z < 0.2:
                kind = 'boot'
            elif len(component) < 60:
                kind = 'accessory'
            if variant == 'triangles':
                part = obj.name.rsplit('_', 1)[-1]
                kind = {'2': 'head', '8': 'head', '9': 'head', '11': 'head',
                        '3': 'boot', '5': 'boot', '6': 'arm', '7': 'arm',
                        '4': 'accessory', '10': 'accessory'}.get(part, 'body')
            for i in component:
                component_of[i] = kind
        groups = {bone.name: obj.vertex_groups.new(name=bone.name) for bone in rig.data.bones}
        for vertex in obj.data.vertices:
            x, y, z = vertex.co
            side = 'L' if x > 0 else 'R'
            kind = component_of[vertex.index]
            weights = {}

            def blend_chain(names):
                scores = []
                for name in names:
                    bone = rig.data.bones[name]
                    direction = bone.tail_local - bone.head_local
                    near = bone.head_local + direction * max(0, min(1, (vertex.co - bone.head_local).dot(direction) / direction.length_squared))
                    scores.append((1 / max((vertex.co - near).length, 0.025) ** 3, name))
                scores = sorted(scores, reverse=True)[:3]
                total = sum((score for score, name in scores))
                return {name: score / total for score, name in scores}
            if kind == 'arm':
                weights = blend_chain(['upper_arm.' + side, 'forearm.' + side, 'hand.' + side])
            elif kind == 'head':
                weights = {'head': 1}
            elif kind == 'cape_head':
                head = smooth(1.44, 1.57, z)
                weights = {'chest': 1 - head, 'head': head}
            elif kind == 'boot':
                shin = smooth(0.12, 0.3, z)
                weights = {'foot.' + side: 1 - shin, 'shin.' + side: shin}
            elif kind == 'accessory':
                weights = {'chest' if z > 1.17 else 'pelvis': 1}
            elif z < 0.95:
                weights = blend_chain(['pelvis', 'thigh.' + side, 'shin.' + side])
            else:
                weights = blend_chain(['pelvis', 'spine', 'chest', 'neck'])
                if variant == 'topology':
                    arm = smooth(0.10, 0.21, abs(x)) * smooth(1.09, 1.27, z) * (1 - smooth(1.44, 1.51, z))
                else:
                    arm = smooth(0.12, 0.25, abs(x)) * smooth(1.10, 1.24, z) * (1 - smooth(1.44, 1.50, z))
                weights = {name: weight * (1 - arm) for name, weight in weights.items()}
                weights['upper_arm.' + side] = arm
            weights = sorted(weights.items(), key=lambda item: item[1], reverse=True)[:4]
            total = sum((weight for name, weight in weights))
            for name, weight in weights:
                if weight > 0:
                    groups[name].add([vertex.index], weight / total, 'REPLACE')
        modifier = obj.modifiers.new('Skin', 'ARMATURE')
        modifier.object = rig
        obj.parent = rig
    if variant == 'topology':
        for side, sign in [('L', 1), ('R', -1)]:
            bone = rig.data.bones['upper_arm.' + side]
            start = bone.head_local.copy()
            end = bone.tail_local.copy() + Vector((0, 0, -0.04))
            direction = end - start
            bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=12, location=(start + end) / 2)
            bridge = bpy.context.object
            bridge.name = 'UnderSleeveUpperArm.' + side
            bridge.rotation_mode = 'QUATERNION'
            bridge.rotation_quaternion = direction.to_track_quat('Z', 'Y')
            bridge.scale = (0.055, 0.052, direction.length / 2 + 0.045)
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
            group = bridge.vertex_groups.new(name='upper_arm.' + side)
            group.add(list(range(len(bridge.data.vertices))), 1.0, 'REPLACE')
            modifier = bridge.modifiers.new('Skin', 'ARMATURE')
            modifier.object = rig
            bridge.parent = rig
            for face in bridge.data.polygons:
                face.use_smooth = True
            meshes.append(bridge)
    scene = bpy.context.scene
    scene.render.fps = 30
    rig.animation_data_create()

    def rotate(name, angle, axis=(-1, 0, 0)):
        pb = rig.pose.bones[name]
        local_axis = pb.bone.matrix_local.to_3x3().inverted() @ Vector(axis)
        pb.rotation_quaternion = Quaternion(local_axis, angle)
    for name in ['idle', 'walk', 'run', 'arms_overhead', 'elbow_bend', 'deep_squat']:
        action = bpy.data.actions.new(name)
        rig.animation_data.action = action
        duration = 60 if name not in ['walk', 'run'] else 30 if name == 'walk' else 22
        for frame in range(1, duration + 2):
            t = (frame - 1) / duration
            wave = math.sin(t * math.tau)
            stress = (1 - math.cos(t * math.tau)) / 2
            for pb in rig.pose.bones:
                pb.rotation_mode = 'QUATERNION'
                pb.rotation_quaternion = Quaternion()
                pb.location = (0, 0, 0)
            drop = -0.32 * stress if name == 'deep_squat' else 0.0
            if name in ['walk', 'run']:
                drop = (-0.05 if name == 'walk' else -0.1) + (0.01 if name == 'walk' else 0.02) * math.cos(t * math.tau * 2)
            rig.pose.bones['pelvis'].location.y = drop
            for side, sign in [('L', 1), ('R', -1)]:
                phase = t * math.tau + (0 if sign == 1 else math.pi)
                ankle_y = 0.0
                ankle_z = 0.12
                if name in ['walk', 'run']:
                    stride = 0.19 if name == 'walk' else 0.3
                    ankle_y = stride * math.cos(phase)
                    ankle_z += (0.1 if name == 'walk' else 0.19) * max(0, math.sin(phase))
                    rotate('upper_arm.' + side, -0.32 * math.cos(phase) if name == 'walk' else -0.65 * math.cos(phase))
                    rotate('forearm.' + side, -0.2 if name == 'walk' else -0.65)
                if name in ['walk', 'run', 'deep_squat']:
                    dy = ankle_y
                    dz = ankle_z - (0.93 + drop)
                    l1 = 0.43
                    l2 = 0.38
                    distance = min(math.hypot(dy, dz), l1 + l2 - 0.001)
                    thigh = math.atan2(dy, -dz) - math.acos(max(-1, min(1, (l1 * l1 + distance * distance - l2 * l2) / (2 * l1 * distance))))
                    knee = math.pi - math.acos(max(-1, min(1, (l1 * l1 + l2 * l2 - distance * distance) / (2 * l1 * l2))))
                    rotate('thigh.' + side, thigh)
                    rotate('shin.' + side, knee)
                    rotate('foot.' + side, -thigh - knee)
                if name == 'arms_overhead':
                    rotate('upper_arm.' + side, -sign * stress * 2.8, (0, 1, 0))
                if name == 'elbow_bend':
                    rotate('forearm.' + side, -stress * 1.8)
                if name == 'deep_squat':
                    rotate('upper_arm.' + side, -stress * 0.65)
            # Resolve arm orientation in world space, then convert through each rest basis.
            # This keeps A-pose and T-pose inputs on the same anatomical motion.
            for side, sign in [('L', 1), ('R', -1)]:
                phase = t * math.tau + (0 if sign == 1 else math.pi)
                swing = 0.0
                bend = 0.0
                if name in ['walk', 'run']:
                    swing = (0.32 if name == 'walk' else 0.65) * math.cos(phase)
                    bend = 0.2 if name == 'walk' else 0.65
                elif name == 'elbow_bend':
                    bend = stress * 1.8
                elif name == 'deep_squat':
                    swing = stress * 0.65
                elevation = -sign * stress * 2.8 if name == 'arms_overhead' else 0.0
                neutral = Vector((sign * 0.15, 0, -0.99)).normalized()
                desired = Quaternion(Vector((0, 1, 0)), elevation) @ (Quaternion(Vector((1, 0, 0)), swing) @ neutral)
                upper = rig.pose.bones['upper_arm.' + side]
                rest_direction = (upper.bone.tail_local - upper.bone.head_local).normalized()
                world_rotation = rest_direction.rotation_difference(desired)
                rest_basis = upper.bone.matrix_local.to_quaternion()
                upper.rotation_quaternion = rest_basis.inverted() @ world_rotation @ rest_basis
                forearm = rig.pose.bones['forearm.' + side]
                elbow_axis = world_rotation.inverted() @ Vector((1, 0, 0))
                basis = forearm.bone.matrix_local.to_quaternion()
                forearm.rotation_quaternion = Quaternion(basis.inverted() @ elbow_axis, bend)
            if name == 'idle':
                rotate('chest', wave * 0.012)
            elif name in ['walk', 'run']:
                rotate('chest', 0.06 if name == 'walk' else 0.14)
            elif name == 'deep_squat':
                rotate('chest', 0.12 * stress)
            for pb in rig.pose.bones:
                pb.keyframe_insert('rotation_quaternion', frame=frame)
                pb.keyframe_insert('location', frame=frame)
        track = rig.animation_data.nla_tracks.new()
        track.name = name
        track.strips.new(name, 1, action)
        track.mute = True
    rig.animation_data.action = None
    for track in rig.animation_data.nla_tracks:
        track.mute = False
    scene.frame_set(1)
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True)
    for o in meshes:
        o.select_set(True)
    bpy.context.preferences.filepaths.save_version = 0
    source = ROOT / 'assets_source/characters/ranger' / ('comparison_' + variant + '.blend')
    bpy.ops.wm.save_as_mainfile(filepath=str(source))
    bpy.ops.export_scene.gltf(filepath=str(OUT / (variant + '.glb')), export_format='GLB', use_selection=True, export_animation_mode='NLA_TRACKS')
    report.append({'variant': variant, 'vertices': sum((len(o.data.vertices) for o in meshes)), 'seconds': round(time.monotonic() - started, 2), 'method': 'component-aware corrected garment weights; analytic leg targets and rest-axis quaternion animation'})
(ROOT / 'docs/ACTION_COMPARISON_BUILD.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
