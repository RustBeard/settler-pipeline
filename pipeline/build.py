# Build a smooth low-poly chibi settler, rig it and add an in-place walk cycle.
# Units: 1 Blender unit = 1 sprite pixel. Character faces -Y. Ground at z=0.
import bpy, bmesh, math, sys, json
from mathutils import Vector, Matrix

P = json.load(open(sys.argv[sys.argv.index("--") + 1])) if "--" in sys.argv else {}
def p(k, d): return P.get(k, d)

import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import OUT, RAW, PX, HERE, ROOT

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene

# --- materials (plain Principled, good for glTF) ---
def mat(name, rgb):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = 0.8
    return m
M_SKIN = mat("skin", (0.85, 0.85, 0.85))
M_EYE = mat("eye", (0.0, 0.0, 0.0))
M_HAIR = mat("hair", (0.25, 0.17, 0.11))

# --- parts (simple primitives) ---
# head = superellipsoid (rounded cube), body = cylinder, hands and feet = spheres
HEAD_C, HEAD_R = p("head_c", [0, 0, 9.5]), p("head_r", [4.7, 4.7, 4.5])
BODY_C, BODY_R, BODY_H = p("body_c", [0, 0, 3.0]), p("body_radius", 2.2), p("body_height", 3.6)
HAND_X, HAND_Y, HAND_Z, HAND_R = p("hand_x", 4.3), p("hand_y", 0.0), p("hand_z", 2.6), p("hand_radius", 1.25)
FOOT_X, FOOT_Y, FOOT_R = p("foot_x", 1.35), p("foot_y", -0.6), p("foot_radius", 1.05)
parts = {
    "head": (HEAD_C, HEAD_R),
    "body": (BODY_C, (BODY_R, BODY_R, BODY_H / 2)),
    "hand.L": ((HAND_X, HAND_Y, HAND_Z), (HAND_R,) * 3),
    "hand.R": ((-HAND_X, HAND_Y, HAND_Z), (HAND_R,) * 3),
    "foot.L": ((FOOT_X, FOOT_Y, FOOT_R), (FOOT_R,) * 3),
    "foot.R": ((-FOOT_X, FOOT_Y, FOOT_R), (FOOT_R,) * 3),
}

mesh_objs = []
for name, (c, r) in parts.items():
    if name == "head":
        # superellipsoid: exponent 2 = sphere, higher = closer to a cube
        n = p("head_roundness_n", 3.0)
        bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=22, radius=1, location=c)
        o = bpy.context.active_object
        sp = lambda v: math.copysign(abs(v) ** (2 / n), v)
        for v in o.data.vertices:
            v.co = Vector((sp(v.co.x), sp(v.co.y), sp(v.co.z)))
    elif name == "body":
        bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=1, depth=2, location=c)
        o = bpy.context.active_object
    else:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8, radius=1, location=c)
        o = bpy.context.active_object
    o.name = name
    o.scale = r
    bpy.ops.object.transform_apply(scale=True)
    o.data.materials.append(M_SKIN)
    vg = o.vertex_groups.new(name=name)
    vg.add(list(range(len(o.data.vertices))), 1.0, "REPLACE")
    mesh_objs.append(o)

# eyes: small vertical capsules sitting on the head surface, bone = head
hc, hr = Vector(HEAD_C), Vector(HEAD_R)
eye_dx, eye_dz = p("eye_dx", 2.0), p("eye_dz", -1.2)
for side, sx in (("L", 1), ("R", -1)):
    x = sx * eye_dx
    z = hc.z + eye_dz
    # point on ellipsoid front (-Y) at given x,z
    # find the head surface in front of the eye by ray casting along +Y
    bpy.context.view_layer.update(); head_obj = bpy.data.objects["head"]
    inv = head_obj.matrix_world.inverted()
    hit, loc, _, _ = head_obj.ray_cast(inv @ Vector((x, -50, z)), Vector((0, 1, 0)))
    y = (head_obj.matrix_world @ loc).y + p("eye_inset", -0.05)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=8, ring_count=6, radius=1, location=(x, y, z))
    e = bpy.context.active_object
    e.name = f"eye.{side}"
    e.scale = p("eye_r", [0.45, 0.4, 0.95])
    bpy.ops.object.transform_apply(scale=True)
    e.data.materials.append(M_EYE)
    vg = e.vertex_groups.new(name="head")
    vg.add(list(range(len(e.data.vertices))), 1.0, "REPLACE")
    mesh_objs.append(e)

for o in mesh_objs:
    # smooth everywhere except the flat caps of the cylinder body
    for f in o.data.polygons: f.use_smooth = not (o.name == "body" and abs(f.normal.z) > 0.9)
    # face tag so the renderer can color eyes black
    # buzz cut: head faces above a hairline that is high at the forehead and low at the nape
    h = o.data.attributes.new("is_hair", "BOOLEAN", "FACE")
    if o.name == "head" and p("hair", True):
        o.data.materials.append(M_HAIR)
        hf, hs, hb = p("hairline_front", 0.45), p("hairline_side", 0.1), p("hairline_back", -0.45)
        for f in o.data.polygons:
            c = (f.center - Vector(HEAD_C)); c = Vector((c.x / HEAD_R[0], c.y / HEAD_R[1], c.z / HEAD_R[2]))
            fr = -c.y / max(1e-6, math.hypot(c.x, c.y))  # 1 = forehead (-Y), -1 = nape
            thr = hs + (hf - hs) * fr if fr > 0 else hs + (hs - hb) * fr
            hit = c.z > thr
            h.data[f.index].value = hit
            if hit: f.material_index = 1
    a = o.data.attributes.new("is_eye", "BOOLEAN", "FACE")
    for d in a.data: d.value = o.name.startswith("eye")

# join into one mesh
bpy.ops.object.select_all(action="DESELECT")
for o in mesh_objs: o.select_set(True)
bpy.context.view_layer.objects.active = mesh_objs[0]
bpy.ops.object.join()
body = bpy.context.active_object
body.name = "Settler"; body.data.name = "Settler"

# --- armature: bones point up (+Z) ---
bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
arm = bpy.context.active_object
arm.name = "Rig"
eb = arm.data.edit_bones
root = eb[0]; root.name = "root"; root.head = (0, 0, 0); root.tail = (0, 1.5, 0)
def bone(name, head, length, parent):
    b = eb.new(name); b.head = head; b.tail = (head[0], head[1], head[2] + length); b.parent = parent
    return b
b_body = bone("body", (0, 0, parts["body"][0][2] - 1.5), 3.0, root)
bone("head", (0, 0, hc.z - hr.z + 0.5), hr.z * 2 - 1, b_body)
bone("hand.L", tuple(parts["hand.L"][0]), 1.2, b_body)
bone("hand.R", tuple(parts["hand.R"][0]), 1.2, b_body)
bone("foot.L", tuple(parts["foot.L"][0]), 1.0, root)
bone("foot.R", tuple(parts["foot.R"][0]), 1.0, root)
bpy.ops.object.mode_set(mode="OBJECT")

body.parent = arm
mod = body.modifiers.new("Armature", "ARMATURE"); mod.object = arm

# --- walk cycle (in place), sampled on every frame, loops cleanly ---
N = p("walk_frames", 16)
act = bpy.data.actions.new("walk")
arm.animation_data_create(); arm.animation_data.action = act
scn.frame_start, scn.frame_end = 0, N
scn.render.fps = p("fps", 12)
pb = arm.pose.bones

def set_loc(bname, world_off, f):
    b = pb[bname]
    R = arm.data.bones[bname].matrix_local.to_3x3()
    b.location = R.inverted() @ Vector(world_off)
    b.keyframe_insert("location", frame=f)
def set_rot(bname, axis_world, ang, f):
    b = pb[bname]
    b.rotation_mode = "XYZ"
    R = arm.data.bones[bname].matrix_local.to_3x3()
    ax = R.inverted() @ Vector(axis_world)
    b.rotation_euler = Matrix.Rotation(ang, 3, ax).to_euler("XYZ")
    b.keyframe_insert("rotation_euler", frame=f)

# expressive walk for tiny sprites: long stance phase, feet reach further back than forward,
# big arm swing on an arc, body+head bob by exactly 1 screen pixel
STANCE = p("stance", 0.6)                       # share of the cycle a foot is planted
F_FRONT, F_BACK = p("stride_front", 1.4), p("stride_back", 2.2)
LIFT = p("lift", 1.5)
H_SWING, H_ARC = p("hand_swing", 2.0), p("hand_arc", 1.0)
H_CROSS = p("hand_cross", 0.0)                   # sideways hand travel toward the body midline
H_EVEN = p("hand_even", 0.0)                     # 0 = hands copy the feet, 1 = even forward/back timing
BOB_UP = p("bob_up", None)                       # share of each step the body is up (None = up only at swing peak)
STEP = 1 / math.cos(math.radians(p("elev_deg", 30)))  # z offset that moves 1 screen pixel

KICK = p("heel_kick", 0.0)                       # 0 = lift peaks mid-swing, 1 = peaks early (foot still behind)
T_PEAK = 0.5 - 0.3 * KICK                        # swing progress at which the foot is highest

def foot_cycle(u):
    """u in [0,1): returns (y, z, swing_height); -y is forward.
    swing_height is the unshifted 0..1 swing arc, used for the body bob so heel_kick doesn't move it."""
    u %= 1.0
    if u < STANCE:                               # planted: slides from front to back
        t = u / STANCE
        return -F_FRONT + (F_FRONT + F_BACK) * t, 0.0, 0.0
    t = (u - STANCE) / (1 - STANCE)              # swing: lifts and moves forward
    # heel_kick also delays the forward travel, so the lifted foot stays behind the body for a while
    d = 0.35 * KICK
    ty = max(0.0, (t - d) / (1 - d))
    e = 0.5 - 0.5 * math.cos(math.pi * ty)
    # remap t so the lift peak lands at T_PEAK (heel kicks up behind the body before swinging forward)
    w = 0.5 * t / T_PEAK if t < T_PEAK else 0.5 + 0.5 * (t - T_PEAK) / (1 - T_PEAK)
    return F_BACK - (F_FRONT + F_BACK) * e, LIFT * math.sin(math.pi * w), math.sin(math.pi * t)

for f in range(N + 1):  # include frame N = frame 0 for smooth looping in glTF
    u = (f + p("phase_offset", 0)) / N
    mid = (F_BACK - F_FRONT) / 2; half = (F_FRONT + F_BACK) / 2
    up = False
    for side, off in (("L", 0.0), ("R", 0.5)):
        y, z, sh = foot_cycle(u + off)
        set_loc(f"foot.{side}", (0, y, z), f)
        up = up or sh > 0.7
        n = (y - mid) / half                     # +1 = foot far back
        # hand_even blends from "copy the foot" (fast back swing during the foot's short swing phase)
        # to an even sine: half the cycle forward, half back; peaks when the same-side foot is furthest back
        n_even = math.cos(2 * math.pi * ((u + off) % 1.0 - STANCE))
        n = (1 - H_EVEN) * n + H_EVEN * n_even
        hy = -H_SWING * n                        # hand goes forward when the same-side foot is back
        hz = H_ARC * max(0.0, -hy / H_SWING) + 0.3 * H_ARC * max(0.0, hy / H_SWING)
        # cross-body swing: the forward hand moves toward the midline, the back hand slightly outward,
        # so the arm swing also reads sideways in the S and N views
        sx = 1 if side == "L" else -1
        hx = -sx * H_CROSS * (n if n > 0 else 0.5 * n)
        set_loc(f"hand.{side}", (hx, hy, hz), f)
    if BOB_UP is not None:
        # step-based bob: each step (half cycle) starts at a heel strike; the body is down for the
        # first (1 - BOB_UP) of the step (weight landing) and up for the rest
        s = (2 * u) % 1.0
        up = s >= 1 - BOB_UP
    set_loc("body", (0, 0, STEP if up else 0.0), f)
    set_loc("head", (0, 0, 0.0), f)

for fc in act.fcurves if hasattr(act, "fcurves") else []:
    for k in fc.keyframe_points: k.interpolation = "LINEAR"

bpy.ops.wm.save_as_mainfile(filepath=f"{OUT}/settler.blend")
bpy.ops.export_scene.gltf(filepath=f"{OUT}/settler.glb", export_format="GLB", export_animations=True)
print("OK", len(body.data.vertices), "verts")
