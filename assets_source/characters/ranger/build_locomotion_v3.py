"""Bake weight-shifted locomotion, skinned finger fists, and held-pose qinggong evasion."""
import json
import math
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector

ROOT = Path(__file__).resolve().parents[3]
bpy.ops.wm.open_mainfile(filepath=str(ROOT / "assets_source/characters/ranger/locomotion_motion_reference.blend"))
scene = bpy.context.scene
scene.render.fps = 30
rig = next(obj for obj in scene.objects if obj.type == "ARMATURE")
meshes = [obj for obj in scene.objects if obj.type == "MESH"
          and any(modifier.type == "ARMATURE" and modifier.object == rig for modifier in obj.modifiers)]
for obj in list(scene.objects):
    if obj.type == "MESH" and obj not in meshes:
        bpy.data.objects.remove(obj, do_unlink=True)
tracks = rig.animation_data.nla_tracks
source_poses = {}
source_feet = {}
for name, duration in (("idle", 60), ("walk", 34), ("run", 22)):
    for track in tracks:
        track.mute = track.name != name
    poses = []
    feet = []
    for frame in range(1, duration + 2):
        scene.frame_set(frame)
        poses.append({bone.name: bone.matrix_basis.copy() for bone in rig.pose.bones})
        feet.append({side: rig.pose.bones[side + "_Foot"].matrix.copy() for side in ("L", "R")})
    source_poses[name] = poses
    source_feet[name] = feet
# Keep the current corrected rest skeleton while reading motion from the Tripo reference.
original_objects = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(ROOT / "assets_source/characters/ranger/animation_inputs/tripo_motion_reference.glb"))
reference = next(obj for obj in bpy.data.objects if obj not in original_objects and obj.type == "ARMATURE")
reference.animation_data.action = None
conversion = Matrix.Rotation(math.pi / 2, 4, "Z")
reference_rest = {bone.name: (conversion @ bone.matrix_local).to_quaternion() for bone in reference.data.bones}
reference_clips = {}
leg_scale = (rig.data.bones["L_Thigh"].length + rig.data.bones["L_Calf"].length) / (reference.data.bones["L_Thigh"].length + reference.data.bones["L_Calf"].length)
for track in reference.animation_data.nla_tracks:
    for other in reference.animation_data.nla_tracks:
        other.mute = other != track
    strip = track.strips[0]
    count = round(strip.frame_end - strip.frame_start)
    frames = []
    for index in range(count + 1):
        frame = strip.frame_start + (strip.frame_end - strip.frame_start) * index / count
        scene.frame_set(math.floor(frame), subframe=frame % 1)
        frames.append({bone.name: conversion @ bone.matrix for bone in reference.pose.bones})
    if track.name == "run":
        # Spread the reference's endpoint drift across the cycle instead of
        # slowing the final steps into a fixed first pose.
        first = frames[0]
        last = frames[-1]
        rotations = {name: first[name].to_quaternion() @ last[name].to_quaternion().inverted() for name in first}
        translations = {name: last[name].translation - first[name].translation for name in first}
        for index, pose in enumerate(frames):
            fraction = index / count
            for name, matrix in pose.items():
                rotation = Quaternion().slerp(rotations[name], fraction) @ matrix.to_quaternion()
                position = matrix.translation - translations[name] * fraction
                pose[name] = Matrix.Translation(position) @ rotation.to_matrix().to_4x4()
    reference_clips[track.name] = frames
reference_hip_height = reference.data.bones["Hip"].head_local.z
for obj in list(bpy.data.objects):
    if obj not in original_objects:
        bpy.data.objects.remove(obj, do_unlink=True)
# Stand with the ankles under the hips.
for frames in source_feet.values():
    for frame in frames:
        for matrix in frame.values():
            position = matrix.translation.copy()
            position.x *= .68
            matrix.translation = position
neutral = source_poses["idle"][0]
neutral_feet = {side: source_feet["idle"][0][side].translation.copy() for side in ("L", "R")}
rig.animation_data_clear()
rig.animation_data_create()
tracks = rig.animation_data.nla_tracks
for action in list(bpy.data.actions):
    bpy.data.actions.remove(action)
boots = {}
for side in ("L", "R"):
    boots[side] = min([obj for obj in meshes if obj.name in ("tripo_part_3", "tripo_part_5")],
                      key=lambda obj: abs(sum(vertex.co.x for vertex in obj.data.vertices)
                                          / len(obj.data.vertices) - neutral_feet[side].x))


def orient(name, head, direction):
    bone = rig.pose.bones[name]
    rest = bone.bone
    rotation = (rest.tail_local - rest.head_local).normalized().rotation_difference(direction.normalized())
    bone.matrix = (Matrix.Translation(head) @ rotation.to_matrix().to_4x4()
                   @ rest.matrix_local.to_quaternion().to_matrix().to_4x4())
    bpy.context.view_layer.update()


def turn(name, axis, angle):
    bone = rig.pose.bones[name]
    matrix = bone.matrix.copy()
    bone.matrix = (Matrix.Translation(matrix.translation)
                   @ Quaternion(Vector(axis), angle).to_matrix().to_4x4()
                   @ matrix.to_quaternion().to_matrix().to_4x4())
    bpy.context.view_layer.update()


def envelope(time, keys):
    for (start, value), (end, next_value) in zip(keys, keys[1:]):
        if time <= end:
            fraction = max(0, (time - start) / (end - start))
            fraction = fraction * fraction * (3 - 2 * fraction)
            return value + (next_value - value) * fraction
    return keys[-1][1]


def solve_leg(side, target, rotation):
    thigh = rig.pose.bones[side + "_Thigh"]
    calf = rig.pose.bones[side + "_Calf"]
    hip = thigh.head.copy()
    delta = target - hip
    distance = min(delta.length, thigh.bone.length + calf.bone.length - .001)
    axis = delta.normalized()
    pole = Vector((-.05 if side == "L" else .05, 1, 0))
    pole = (pole - axis * pole.dot(axis)).normalized()
    along = (thigh.bone.length ** 2 - calf.bone.length ** 2 + distance ** 2) / (2 * distance)
    height = math.sqrt(max(0, thigh.bone.length ** 2 - along ** 2))
    knee = hip + axis * along + pole * height
    orient(thigh.name, hip, knee - hip)
    orient(calf.name, knee, target - knee)
    foot = rig.pose.bones[side + "_Foot"]
    foot.matrix = Matrix.Translation(target) @ rotation.to_matrix().to_4x4()
    bpy.context.view_layer.update()


def plant_foot(side, target, support, rotation):
    solve_leg(side, target, rotation)
    for correction in range(4):
        evaluated = boots[side].evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh = evaluated.to_mesh()
        bottom = min((evaluated.matrix_world @ vertex.co).z for vertex in mesh.vertices)
        evaluated.to_mesh_clear()
        if abs(bottom) < .00005 or (not support and bottom >= 0):
            break
        target.z -= bottom
        solve_leg(side, target, rotation)


def align_lower_leg_skin():
    """Center the visible boot shaft on the solved leg, preserving its cross-section."""
    profiles = {}
    for side in ("L", "R"):
        obj = boots[side]
        evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh = evaluated.to_mesh()
        positions = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
        calf = rig.pose.bones[side + "_Calf"]
        profile = []
        for height in (.06, .12, .20, .28, .35):
            section = [position.x for position in positions if abs(position.z - height) < .025]
            if not section:
                continue
            center = (min(section) + max(section)) * .5
            fraction = max(0, min(1, (height - calf.tail.z) / (calf.head.z - calf.tail.z)))
            desired = calf.tail.x + (calf.head.x - calf.tail.x) * fraction
            profile.append((height, max(-.035, min(.035, desired - center))))
        evaluated.to_mesh_clear()
        profiles[side] = profile
    for obj in meshes:
        if obj.name not in ("tripo_part_1", "tripo_part_3", "tripo_part_5"):
            continue
        evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh = evaluated.to_mesh()
        positions = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
        evaluated.to_mesh_clear()
        for vertex, position in zip(obj.data.vertices, positions):
            if position.z >= .65:
                continue
            side = "L" if position.x < 0 else "R"
            profile = profiles[side]
            offset = profile[0][1]
            for (start, value), (end, next_value) in zip(profile, profile[1:]):
                fraction = max(0, min(1, (position.z - start) / (end - start)))
                offset = value + (next_value - value) * fraction
                if position.z <= end:
                    break
            fade = max(0, min(1, (.65 - position.z) / .2))
            skin = Matrix(((0, 0, 0, 0),) * 4)
            total = 0
            for group in vertex.groups:
                bone = rig.pose.bones.get(obj.vertex_groups[group.group].name)
                if bone:
                    transform = (obj.matrix_world.inverted() @ rig.matrix_world @ bone.matrix
                                 @ bone.bone.matrix_local.inverted() @ rig.matrix_world.inverted() @ obj.matrix_world)
                    skin += transform * group.weight
                    total += group.weight
            if total == 0:
                continue
            correction = skin.to_3x3().inverted_safe() @ (obj.matrix_world.inverted().to_3x3() @ Vector((offset * fade, 0, 0)))
            if obj.data.shape_keys:
                for key in obj.data.shape_keys.key_blocks:
                    key.data[vertex.index].co += correction
            else:
                vertex.co += correction
    bpy.context.view_layer.update()


def pose_arm(side, shoulder_angle, elbow_angle, hand_roll):
    """Swing the bent arm as a pendulum, with a stable wrist and inward-facing palm."""
    sign = -1 if side == "L" else 1
    rotation = Quaternion(Vector((1, 0, 0)), shoulder_angle)
    upper_direction = rotation @ Vector((sign * .10, 0, -1)).normalized()
    fore_direction = rotation @ Vector((sign * .035, math.sin(elbow_angle), -math.cos(elbow_angle))).normalized()
    upper = rig.pose.bones[side + "_Upperarm"]
    orient(upper.name, upper.head.copy(), upper_direction)
    forearm = rig.pose.bones[side + "_Forearm"]
    orient(forearm.name, forearm.head.copy(), fore_direction)
    turn(forearm.name, fore_direction, sign * hand_roll)
    hand = rig.pose.bones[side + "_Hand"]
    orient(hand.name, hand.head.copy(), fore_direction)
    turn(hand.name, fore_direction, sign * hand_roll)


def bake_frame(frame):
    for bone in rig.pose.bones:
        bone.keyframe_insert("location", frame=frame)
        bone.keyframe_insert("rotation_quaternion", frame=frame)
        bone.keyframe_insert("scale", frame=frame)


def finish_action(name, action):
    track = tracks.new()
    track.name = name
    track.strips.new(name, 1, action)
    track.mute = True
    rig.animation_data.action = None


# Joint locations are fitted to the existing hand silhouettes in the normalized source.
# Each digit receives three weighted, connected phalanges.
finger_layout = {
    "Index": [(0.077, .039), (.116, .039), (.143, .039), (.163, .039)],
    "Middle": [(.078, .015), (.121, .015), (.153, .015), (.177, .015)],
    "Ring": [(.073, -.011), (.114, -.011), (.143, -.012), (.165, -.012)],
    "Little": [(.059, -.034), (.090, -.036), (.115, -.038), (.137, -.039)],
    "Thumb": [(.025, .040), (.050, .061), (.073, .073), (.090, .075)],
}
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode="EDIT")
for side, sign in (("L", -1), ("R", 1)):
    wrist = rig.data.edit_bones[side + "_Hand"].head.copy()
    for finger, points in finger_layout.items():
        parent = rig.data.edit_bones[side + "_Hand"]
        for segment in range(3):
            bone = rig.data.edit_bones.new(f"{side}_{finger}{segment + 1:02d}")
            start, end = points[segment], points[segment + 1]
            bone.head = Vector((wrist.x + sign * start[0], start[1], 1.326))
            bone.tail = Vector((wrist.x + sign * end[0], end[1], 1.326))
            bone.parent = parent
            bone.use_connect = segment > 0
            bone.align_roll(Vector((0, 0, 1)))
            parent = bone
bpy.ops.object.mode_set(mode="OBJECT")
for bone in rig.pose.bones:
    bone.rotation_mode = "QUATERNION"
    neutral.setdefault(bone.name, Matrix.Identity(4))

finger_weights = {}
for side, sign in (("L", -1), ("R", 1)):
    wrist = rig.data.bones[side + "_Hand"].head_local.x
    for mesh in meshes:
        hand_group = mesh.vertex_groups.get(side + "_Hand")
        if hand_group is None:
            continue
        groups = {finger: [mesh.vertex_groups.new(name=f"{side}_{finger}{segment + 1:02d}")
                           for segment in range(3)] for finger in finger_layout}
        for vertex in mesh.data.vertices:
            original_weight = sum(item.weight for item in vertex.groups if item.group == hand_group.index)
            if original_weight < .001:
                continue
            length = sign * (vertex.co.x - wrist)
            y = vertex.co.y
            if y > .053 and length < .105:
                finger = "Thumb"
            else:
                finger = min((name for name in finger_layout if name != "Thumb"),
                             key=lambda name: abs(y - finger_layout[name][0][1]))
            points = finger_layout[finger]
            start = Vector((points[0][0], points[0][1]))
            end = Vector((points[-1][0], points[-1][1]))
            axis = (end - start).normalized()
            along = (Vector((length, y)) - start).dot(axis)
            fade = max(0.0, min(1.0, (along + .006) / .018))
            fade = fade * fade * (3 - 2 * fade)
            amount = original_weight * fade
            if amount < .0001:
                continue
            centers = [(Vector(point) - start).dot(axis) for point in points[:-1]]
            # Blend across the next knuckle over a short interval to avoid rigid seams.
            weights = [1.0, 0.0, 0.0]
            for joint in (1, 2):
                blend = max(0.0, min(1.0, (along - centers[joint] + .006) / .012))
                weights[joint - 1] *= 1 - blend
                weights[joint] = blend
            total = sum(weights)
            hand_group.add([vertex.index], original_weight - amount, "REPLACE")
            for group, weight in zip(groups[finger], weights):
                if weight > 0:
                    group.add([vertex.index], amount * weight / total, "REPLACE")
        for finger, digit_groups in groups.items():
            for group in digit_groups:
                count = sum(any(item.group == group.index and item.weight > .001 for item in vertex.groups)
                            for vertex in mesh.data.vertices)
                finger_weights[group.name] = finger_weights.get(group.name, 0) + count


def reset_pose(pose):
    for bone in rig.pose.bones:
        bone.matrix_basis = pose.get(bone.name, Matrix.Identity(4))
    bpy.context.view_layer.update()


def fist(side, amount):
    sign = -1 if side == "L" else 1
    for finger in finger_layout:
        angles = (65, 90, 60) if finger != "Thumb" else (25, 55, 40)
        for segment, angle in enumerate(angles):
            bone = rig.pose.bones[f"{side}_{finger}{segment + 1:02d}"]
            curl = Quaternion(Vector((1, 0, 0)), -math.radians(angle) * amount)
            oppose = Quaternion(Vector((0, 0, 1)), -sign * .65 * amount if finger == "Thumb" and segment == 0 else 0)
            bone.rotation_quaternion = oppose @ curl
    bpy.context.view_layer.update()


def aligned_foot_rotation(side, rotation):
    direction = rotation @ Vector((0, 1, 0))
    yaw = math.atan2(direction.x, direction.y)
    desired = math.radians(6) * (-1 if side == "L" else 1)
    return Quaternion(Vector((0, 0, 1)), yaw - desired) @ rotation


def foot_rotation(side, pitch):
    base = aligned_foot_rotation(side, source_feet["idle"][0][side].to_quaternion())
    return Quaternion(Vector((1, 0, 0)), pitch) @ base


def travel(time):
    """Hermite root translation, with sustained travel through the held airborne pose."""
    keys = [(0, 0, 0), (.12, 0, 0), (.22, .12, 1.8), (.64, .86, 1.7), (.84, 1, 0), (1, 1, 0)]
    for (start, value, slope), (end, next_value, next_slope) in zip(keys, keys[1:]):
        if time <= end:
            width = end - start
            t = max(0, (time - start) / width)
            return ((2 * t ** 3 - 3 * t ** 2 + 1) * value
                    + (t ** 3 - 2 * t ** 2 + t) * width * slope
                    + (-2 * t ** 3 + 3 * t ** 2) * next_value
                    + (t ** 3 - t ** 2) * width * next_slope)
    return 1.0


report = {"fps": 30, "bones": len(rig.data.bones), "finger_weighted_vertices": finger_weights, "actions": {}}
# Original idle remains the neutral pose used at the dodge boundaries.
action = bpy.data.actions.new("idle")
rig.animation_data.action = action
samples = []
for frame, pose in enumerate(source_poses["idle"]):
    scene.frame_set(frame + 1)
    reset_pose(pose)
    for side in ("L", "R"):
        plant_foot(side, neutral_feet[side].copy(), True, foot_rotation(side, 0))
        fist(side, .28)
    if frame == 0:
        align_lower_leg_skin()
        idle_neutral = {bone.name: bone.matrix_basis.copy() for bone in rig.pose.bones}
    bake_frame(frame + 1)
    samples.append({"frame": frame + 1, "contacts": {"L": True, "R": True}, "root_displacement": [0, 0, 0]})
finish_action("idle", action)
report["actions"]["idle"] = samples

ordered_bones = sorted([bone for bone in rig.pose.bones if bone.name in reference_rest], key=lambda bone: len(bone.parent_recursive))
for name, frames in reference_clips.items():
    action = bpy.data.actions.new(name)
    rig.animation_data.action = action
    samples = []
    duration = len(frames) - 1
    feet_floor = {side: min(frame[side + "_Foot"].translation.z for frame in frames) for side in ("L", "R")}
    lateral_center = {side: sum((frame[side + "_Foot"].translation - frame["Hip"].translation).x for frame in frames) / len(frames) for side in ("L", "R")}
    forward_center = {side: sum((frame[side + "_Foot"].translation - frame["Hip"].translation).y for frame in frames) / len(frames) for side in ("L", "R")}
    for index, source in enumerate(frames):
        scene.frame_set(index + 1)
        reset_pose(neutral)
        for bone in ordered_bones:
            if bone.name == "Root":
                continue
            rotation = source[bone.name].to_quaternion() @ reference_rest[bone.name].inverted() @ bone.bone.matrix_local.to_quaternion()
            bone.matrix = Matrix.Translation(bone.head.copy()) @ rotation.to_matrix().to_4x4()
            bpy.context.view_layer.update()
            if bone.name == "Hip":
                matrix = bone.matrix.copy()
                matrix.translation = rig.data.bones["Hip"].head_local.copy()
                matrix.translation.z += (source["Hip"].translation.z - reference_hip_height) * leg_scale
                matrix.translation.z -= {"walk": .005, "look_around": .025, "run": 0}[name]
                if name == "run":
                    matrix.translation.y += .075
                bone.matrix = matrix
                bpy.context.view_layer.update()
        contacts = {}
        for side, sign in (("L", -1), ("R", 1)):
            relative = source[side + "_Foot"].translation - source["Hip"].translation
            target = neutral_feet[side].copy()
            if name != "look_around":
                target.x += max(-.015, min(.015, (relative.x - lateral_center[side]) * leg_scale * .35))
                target.y += (relative.y - forward_center[side]) * leg_scale * .76
                target.z += max(0, source[side + "_Foot"].translation.z - feet_floor[side]) * leg_scale
            rotation = source[side + "_Foot"].to_quaternion() @ reference_rest[side + "_Foot"].inverted() @ rig.data.bones[side + "_Foot"].matrix_local.to_quaternion()
            # Extract sagittal foot pitch from the reference's anatomical forward axis.
            # Bone-local Y can approach vertical and produce unstable yaw at toe-off.
            delta = source[side + "_Foot"].to_quaternion() @ reference_rest[side + "_Foot"].inverted()
            forward = delta @ Vector((0, 1, 0))
            pitch = math.atan2(forward.z, forward.y)
            rotation = foot_rotation(side, max(-.65, min(.9, pitch)))
            if name == "run":
                solve_leg(side, target, rotation)
                calf = rig.pose.bones[side + "_Calf"]
                shin = (calf.tail - calf.head).normalized()
                shin_pitch = math.atan2(shin.y, -shin.z)
                lift = max(0, min(1, (target.z - neutral_feet[side].z - .04) / .26))
                pitch = max(-.65, min(.9, pitch)) * (1 - lift) + max(-1.15, min(1.15, shin_pitch)) * lift
                rotation = foot_rotation(side, pitch)
            # Keep the boot sole rigid while the ankle supplies the reference pitch.
            rig.pose.bones[side + "_ToeBase"].matrix_basis = neutral[side + "_ToeBase"]
            bpy.context.view_layer.update()
            support = name == "look_around" or target.z - neutral_feet[side].z < .035
            plant_foot(side, target, support, rotation)
            fist(side, .85 if name == "run" else .28)
            contacts[side] = support
        # Ease the last few frames to the first in-place pose for a continuous loop.
        if index == 0:
            first_pose = {bone.name: bone.matrix_basis.copy() for bone in rig.pose.bones}
        seam = 0.0 if index < duration else 1.0
        if name == "look_around":
            seam = 1 - envelope(index / duration, [(0, 0), (.04, 1), (.96, 1), (1, 0)])
        for bone in rig.pose.bones:
            destination = idle_neutral[bone.name] if name == "look_around" else first_pose[bone.name]
            bone.matrix_basis = bone.matrix_basis.lerp(destination, seam)
        bpy.context.view_layer.update()
        for side in ("L", "R"):
            foot = rig.pose.bones[side + "_Foot"]
            plant_foot(side, foot.head.copy(), contacts[side], foot.matrix.to_quaternion())
        bake_frame(index + 1)
        samples.append({"frame": index + 1, "contacts": contacts, "root_displacement": [0, 0, 0]})
    finish_action(name, action)
    report["actions"][name] = samples

directions = {
    "dodge_front": (Vector((0, 1, 0)), 3.30, "L"),
    "dodge_back": (Vector((0, -1, 0)), 2.80, "R"),
    "dodge_left": (Vector((-1, 0, 0)), 3.00, "L"),
    "dodge_right": (Vector((1, 0, 0)), 3.00, "R"),
}
for name, (direction, distance, lead_side) in directions.items():
    action = bpy.data.actions.new(name)
    rig.animation_data.action = action
    samples = []
    duration = 24
    for frame in range(duration + 1):
        scene.frame_set(frame + 1)
        reset_pose(neutral)
        time = frame / duration
        hold = envelope(time, [(0, 0), (.12, .35), (.22, 1), (.64, 1), (.82, .35), (1, 0)])
        air = envelope(time, [(0, 0), (.12, 0), (.22, .09), (.64, .09), (.80, 0), (1, 0)])
        displacement = direction * distance * travel(time) + Vector((0, 0, air))
        root = rig.pose.bones["Root"]
        matrix = root.matrix.copy()
        matrix.translation += displacement
        root.matrix = matrix
        bpy.context.view_layer.update()
        absorption = envelope(time, [(0, 0), (.64, 0), (.78, .12), (1, 0)])
        hip = rig.pose.bones["Hip"]
        matrix = hip.matrix.copy()
        push_absorption = envelope(time, [(0, 0), (.12, .025), (.18, .025), (.22, 0), (1, 0)])
        matrix.translation += direction * .075 * hold + Vector((0, 0, -.08 * hold - absorption - push_absorption))
        hip.matrix = matrix
        bpy.context.view_layer.update()
        axis = Vector((-direction.y, direction.x, 0))
        lean = (.22 if name == "dodge_back" else .34) * hold
        turn("Hip", axis, lean * .50)
        turn("Waist", axis, lean * .30)
        turn("Spine01", axis, lean * .20)
        turn("Head", axis, -lean * .45)
        contacts = {}
        for side in ("L", "R"):
            leading = side == lead_side
            held = neutral_feet[side] + displacement
            held += direction * (.03 if leading else -.22) * hold
            held.z += (.32 if leading else .015) * hold
            lift_time = .10 if leading else .18
            land_time = .75 if leading else .84
            depart = envelope(time, [(0, 0), (lift_time, 0), (.22, 1), (1, 1)])
            target = neutral_feet[side].lerp(held, depart)
            landing = envelope(time, [(0, 0), (.64, 0), (land_time, 1), (1, 1)])
            final_foot = neutral_feet[side] + direction * distance
            target = target.lerp(final_foot, landing)
            support = time <= lift_time or time >= land_time
            rotation = foot_rotation(side, (.10 if leading else -.18) * hold)
            if leading and hold > 0:
                solve_leg(side, target, rotation)
                calf_axis = rig.pose.bones[side + "_Calf"].tail - rig.pose.bones[side + "_Calf"].head
                shin_down = calf_axis.normalized()
                shin_pitch = math.atan2(shin_down.y, -shin_down.z)
                rotation = foot_rotation(side, max(-1.15, min(1.15, shin_pitch)) * hold)
            plant_foot(side, target, support, rotation)
            contacts[side] = support
            pose_arm(side, (-.10 if leading else .22) * hold,
                     .25 + (.65 if leading else .95) * hold, math.radians(70) * hold)
            for suffix in ("Upperarm", "Forearm", "Hand"):
                bone = rig.pose.bones[side + "_" + suffix]
                bone.matrix_basis = neutral[bone.name].lerp(bone.matrix_basis, hold)
            fist(side, .28 + .35 * hold)
            bpy.context.view_layer.update()
        bake_frame(frame + 1)
        samples.append({"frame": frame + 1, "contacts": contacts,
                        "root_displacement": list(displacement), "lead_side": lead_side,
                        "glide": .22 <= time <= .64})
    finish_action(name, action)
    report["actions"][name] = samples

for track in tracks:
    track.mute = False
scene.frame_set(1)
bpy.ops.object.select_all(action="DESELECT")
rig.select_set(True)
for mesh in meshes:
    mesh.select_set(True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "assets_source/characters/ranger/locomotion_v3.blend"))
bpy.ops.export_scene.gltf(
    filepath=str(ROOT / "Loopbound/assets/characters/ranger/action_comparison/locomotion_v3.glb"),
    export_format="GLB", use_selection=True, export_animation_mode="NLA_TRACKS", export_anim_slide_to_zero=True)
output = ROOT / "local_previews/locomotion_v3"
output.mkdir(parents=True, exist_ok=True)
(output / "build_checks.json").write_text(json.dumps(report, indent=2))
print("LOCOMOTION V3 BUILT: 71 bones, finger fists, body weight shifts, four held-pose glide dodges")



