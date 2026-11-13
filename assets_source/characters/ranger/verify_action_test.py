"""Check both authored rigs, including forward gait and actual deformed boot soles."""
import bpy
import json
from pathlib import Path

root = Path(__file__).resolve().parents[3]
report = {}
for variant in ['topology', 'triangles']:
    bpy.ops.wm.open_mainfile(filepath=str(root / 'assets_source/characters/ranger' / ('comparison_' + variant + '.blend')))
    rig = next(obj for obj in bpy.context.scene.objects if obj.type == 'ARMATURE')
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    boot_vertices = {obj.name: [vertex.index for vertex in obj.data.vertices if vertex.co.z < .32] for obj in meshes}
    results = {}
    for track in rig.animation_data.nla_tracks:
        for other in rig.animation_data.nla_tracks:
            other.mute = other != track
        soles = []
        endpoints = []
        maximum_radius = 0.0
        last_frame = int(track.strips[0].frame_end)
        for frame in range(1, last_frame + 1):
            bpy.context.scene.frame_set(frame)
            graph = bpy.context.evaluated_depsgraph_get()
            points = []
            boot_points = []
            for obj in meshes:
                evaluated = obj.evaluated_get(graph)
                data = evaluated.to_mesh()
                world_points = [evaluated.matrix_world @ vertex.co for vertex in data.vertices]
                points.extend(world_points)
                boot_points.extend(world_points[index] for index in boot_vertices[obj.name])
                evaluated.to_mesh_clear()
            soles.append(min(point.z for point in boot_points))
            maximum_radius = max(maximum_radius, max(point.length for point in points))
            if frame in [1, last_frame]:
                endpoints.append(points)
        loop_error = max((first - last).length for first, last in zip(*endpoints))
        result = {'support_min_z': min(soles), 'support_max_z': max(soles), 'loop_vertex_delta': loop_error, 'max_radius': maximum_radius}
        assert loop_error < .0001, (variant, track.name, 'loop discontinuity', result)
        assert min(soles) > -.02 and max(soles) < .02, (variant, track.name, 'support foot error', result)
        assert maximum_radius < 2.1, (variant, track.name, 'exploded mesh', result)
        if track.name in ['walk', 'run']:
            foot_positions = []
            for phase in [.1, .4, .6, .9]:
                bpy.context.scene.frame_set(1 + int((last_frame - 1) * phase))
                foot_positions.append(rig.pose.bones['foot.L'].head.y)
            assert foot_positions[1] > foot_positions[0], (variant, 'swing must advance toward +Y', foot_positions)
            assert foot_positions[3] < foot_positions[2], (variant, 'stance must travel toward -Y', foot_positions)
            result['forward_gait'] = True
        results[track.name] = result
    report[variant] = results
output = root / 'local_previews/actions/geometry_checks.json'
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
print('PASS both variants: forward gait, floor contact, loop continuity, deformation bounds')
