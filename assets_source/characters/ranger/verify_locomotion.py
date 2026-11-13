"""Check every baked frame, including airborne phases and one-shot endpoints."""
import json
import math
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
variant = "locomotion_v3"
output = ROOT / "local_previews" / variant
schedule = json.loads((output / "build_checks.json").read_text())
bpy.ops.wm.open_mainfile(filepath=str(ROOT / "assets_source/characters/ranger" / (variant + ".blend")))
scene = bpy.context.scene
rig = next(obj for obj in scene.objects if obj.type == "ARMATURE")
meshes = [obj for obj in scene.objects if obj.type == "MESH"
          and any(modifier.type == "ARMATURE" and modifier.object == rig for modifier in obj.modifiers)]
assert len(rig.data.bones) == (71 if variant == "locomotion_v3" else 41)
with bpy.data.libraries.load(str(ROOT / "assets_source/characters/ranger/locomotion_motion_reference.blend")) as (source, target):
    target.armatures = source.armatures
baseline = target.armatures[0]
assert set(baseline.bones.keys()).issubset(rig.data.bones.keys())
for bone in rig.data.bones:
    if bone.name not in baseline.bones:
        continue
    original = baseline.bones[bone.name]
    assert (bone.parent.name if bone.parent else None) == (original.parent.name if original.parent else None)
    assert max(abs(bone.matrix_local[row][column] - original.matrix_local[row][column])
               for row in range(4) for column in range(4)) < 1e-7
boots = {}
for side in ("L", "R"):
    x = rig.data.bones[side + "_Foot"].head_local.x
    boots[side] = min(
        [obj for obj in meshes if obj.name in ("tripo_part_3", "tripo_part_5")],
        key=lambda obj: abs(sum(v.co.x for v in obj.data.vertices) / len(obj.data.vertices) - x))


def vertices(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    values = np.empty(len(mesh.vertices) * 3)
    mesh.vertices.foreach_get("co", values)
    evaluated.to_mesh_clear()
    return values.reshape((-1, 3))


def bend(first, second):
    return math.degrees((first.tail - first.head).angle(second.tail - second.head))


report = {}
neutral_vertices = None
expected = {"idle", "walk", "run", "dodge_front", "dodge_back", "dodge_left", "dodge_right", "look_around"}
assert {track.name for track in rig.animation_data.nla_tracks} == expected

for track in rig.animation_data.nla_tracks:
    for other in rig.animation_data.nla_tracks:
        other.mute = other != track
    name = track.name
    for mesh in meshes:
        keys = mesh.data.shape_keys
        if keys and keys.animation_data:
            for shape_track in keys.animation_data.nla_tracks:
                shape_track.mute = shape_track.name != name
    floor = []
    support_errors = []
    knees = []
    elbows = []
    endpoints = []
    flight_bottoms = []
    ankle_gaps = []
    arm_gap_excess = []
    knee_asymmetry = []
    directional_weight = []
    torso_pitch = []
    glide_poses = []
    glide_heights = []
    glide_ankle_angles = []
    visible_calf_alignment = []
    knee_lateral_offsets = []
    foot_rotation_steps = []
    previous_feet = {}
    for sample in schedule["actions"][name]:
        scene.frame_set(sample["frame"])
        for side in ("L", "R"):
            boot_vertices = vertices(boots[side])
            bottom = float(boot_vertices[:, 2].min())
            if name == "idle" and sample["frame"] == 1:
                calf = rig.pose.bones[side + "_Calf"]
                for height in (.12, .20, .28, .35):
                    section = boot_vertices[np.abs(boot_vertices[:, 2] - height) < .025, 0]
                    if not len(section):
                        continue
                    center = float((section.min() + section.max()) * .5)
                    fraction = (height - calf.tail.z) / (calf.head.z - calf.tail.z)
                    expected = calf.tail.x + (calf.head.x - calf.tail.x) * fraction
                    visible_calf_alignment.append(abs(center - expected))
            floor.append(bottom)
            if sample["contacts"][side]:
                support_errors.append(abs(bottom))
            elif sample.get("air_height", 0) > .30:
                flight_bottoms.append(bottom)
            if name in ("idle", "walk", "run", "look_around"):
                thigh = rig.pose.bones[side + "_Thigh"]
                calf = rig.pose.bones[side + "_Calf"]
                axis = (calf.tail - thigh.head).normalized()
                knee_offset = thigh.tail - thigh.head
                knee_offset -= axis * knee_offset.dot(axis)
                knee_lateral_offsets.append(abs(knee_offset.x))
                rotation = rig.pose.bones[side + "_Foot"].matrix.to_quaternion()
                if side in previous_feet:
                    difference = previous_feet[side].rotation_difference(rotation).angle
                    foot_rotation_steps.append(math.degrees(min(difference, 2 * math.pi - difference)))
                previous_feet[side] = rotation
            knees.append(bend(rig.pose.bones[side + "_Thigh"], rig.pose.bones[side + "_Calf"]))
            ankle_gaps.append((rig.pose.bones[side + "_Calf"].tail - rig.pose.bones[side + "_Foot"].head).length)
            elbows.append(bend(rig.pose.bones[side + "_Upperarm"], rig.pose.bones[side + "_Forearm"]))
            for parent, child in [("Clavicle", "Upperarm"), ("Upperarm", "Forearm"), ("Forearm", "Hand")]:
                first = rig.pose.bones[side + "_" + parent]
                second = rig.pose.bones[side + "_" + child]
                rest_gap = (first.bone.tail_local - second.bone.head_local).length
                arm_gap_excess.append((first.tail - second.head).length - rest_gap)
        for bone in rig.pose.bones:
            assert all(math.isfinite(value) for value in bone.matrix.translation)
        torso = rig.pose.bones["Head"].head - rig.pose.bones["Hip"].head
        torso_pitch.append(math.degrees(math.atan2(torso.y, torso.z)))
        if name.startswith("dodge_"):
            if variant != "locomotion_v3":
                assert any(sample["contacts"].values()), (name, "Both feet airborne")
            if sample.get("glide", False):
                assert not any(sample["contacts"].values())
                lead = sample["lead_side"]
                calf = rig.pose.bones[lead + "_Calf"]
                foot = rig.pose.bones[lead + "_Foot"]
                glide_ankle_angles.append(math.degrees((calf.head - calf.tail).angle(foot.tail - foot.head)))
                root_position = rig.pose.bones["Root"].head
                glide_poses.append(np.array([list(bone.head - root_position) for bone in rig.pose.bones]))
                glide_heights.extend(float(vertices(boots[side])[:, 2].min()) for side in ("L", "R"))
            lead = sample["lead_side"]
            rear = "R" if lead == "L" else "L"
            knee_asymmetry.append(bend(rig.pose.bones[lead + "_Thigh"], rig.pose.bones[lead + "_Calf"])
                                  - bend(rig.pose.bones[rear + "_Thigh"], rig.pose.bones[rear + "_Calf"]))
            direction = np.array(schedule["actions"][name][-1]["root_displacement"])
            direction /= np.linalg.norm(direction)
            hip = rig.pose.bones["Hip"]
            offset = np.array(hip.head) - np.array(hip.bone.head_local) - np.array(sample["root_displacement"])
            directional_weight.append(float(np.dot(offset, direction)))
        if sample == schedule["actions"][name][0] or sample == schedule["actions"][name][-1]:
            endpoints.append(np.concatenate([vertices(obj) for obj in meshes]))
    if name == "idle":
        neutral_vertices = endpoints[0]
    if name.startswith("dodge_"):
        assert float(np.abs(endpoints[0] - neutral_vertices).max()) < .0001, (name, "Idle transition pose")
    displacement = np.array(schedule["actions"][name][-1].get("root_displacement", [0, 0, 0]))
    endpoint_error = float(np.abs(endpoints[0] - (endpoints[-1] - displacement)).max())
    report[name] = {
        "visible_calf_center_error_m": max(visible_calf_alignment, default=0),
        "maximum_knee_lateral_offset_m": max(knee_lateral_offsets, default=0),
        "maximum_foot_rotation_step_deg": max(foot_rotation_steps, default=0),
        "minimum_floor_m": min(floor), "support_error_m": max(support_errors),
        "knee_flexion_deg": [min(knees), max(knees)],
        "elbow_flexion_deg": [min(elbows), max(elbows)],
        "endpoint_vertex_error_m": endpoint_error,
        "jump_peak_minimum_boot_height_m": min(flight_bottoms) if flight_bottoms else None,
        "maximum_ankle_joint_gap_m": max(ankle_gaps),
        "maximum_arm_joint_gap_increase_m": max(arm_gap_excess),
        "maximum_lead_knee_flexion_advantage_deg": max(knee_asymmetry) if knee_asymmetry else None,
        "maximum_directional_pelvis_weight_shift_m": max(directional_weight) if directional_weight else None,
        "torso_forward_pitch_deg": [min(torso_pitch), max(torso_pitch)],
        "glide_relative_pose_drift_m": float(np.max(np.abs(np.array(glide_poses) - glide_poses[0]))) if glide_poses else None,
        "minimum_glide_boot_height_m": min(glide_heights) if glide_heights else None,
        "glide_ankle_angle_deg": [min(glide_ankle_angles), max(glide_ankle_angles)] if glide_ankle_angles else None,
    }
    print(name, report[name], flush=True)
    assert min(floor) > -.008, (name, "floor penetration")
    assert max(support_errors) < .008, (name, "support")
    assert max(knees) < 150, (name, "knee")
    assert max(elbows) < 145, (name, "elbow")
    assert endpoint_error < .0001, (name, "endpoints")
    assert max(ankle_gaps) < .002, (name, "ankle separation", max(ankle_gaps))
    assert max(arm_gap_excess) < .002, (name, "arm separation")
    if name == "jump":
        assert min(flight_bottoms) > .25, "Jump must have a genuine airborne phase"
    if name.startswith("dodge_"):
        assert max(knee_asymmetry) > 20, (name, "Missing single-leg knee bend")
        assert max(directional_weight) > (.07 if variant == "locomotion_v3" else .075), (name, "Missing directional weight shift")
        if variant == "locomotion_v3":
            assert min(glide_ankle_angles) > 55 and max(glide_ankle_angles) < 135, (name, "Ankle overbent")
            assert min(glide_heights) > .025, (name, "Missing airborne glide")
            assert report[name]["glide_relative_pose_drift_m"] < .001, (name, "Glide pose did not hold")
    if visible_calf_alignment:
        assert max(visible_calf_alignment) < .012, (name, "Visible calf diverges from the leg axis")
    if knee_lateral_offsets:
        assert max(knee_lateral_offsets) < .035, (name, "Knees splay outward")
        assert max(foot_rotation_steps) < 35, (name, "Foot rotation discontinuity")
    if variant == "locomotion_v3" and name in ("walk", "run"):
        assert min(torso_pitch) > -12 and max(torso_pitch) < 45, (name, "Torso pitch range")
        if name == "run":
            assert max(elbows) - min(elbows) > 15, "Forearms too rigid"
(output / "verification.json").write_text(json.dumps(report, indent=2))
if variant == "locomotion_v3":
    assert len(schedule["finger_weighted_vertices"]) == 30
    assert min(schedule["finger_weighted_vertices"].values()) >= 3, "Unweighted finger bone"
print("LOCOMOTION CHECK PASS:", variant, len(report), "clips, floor, connections, joint limits, gait, endpoints")
