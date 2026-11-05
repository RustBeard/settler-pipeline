# Render the rigged settler in 8 directions with a top-down ortho camera.
# Each render encodes per-pixel data as flat emission: R = part id, G = depth, B = normal Z.
# Pixel-art conversion happens later in pixelize.py.
import bpy, math, sys, json, os

P = json.load(open(sys.argv[sys.argv.index("--") + 1])) if "--" in sys.argv else {}
def p(k, d): return P.get(k, d)

import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import OUT, RAW, PX, HERE, ROOT
bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT, "settler.blend"))
scn = bpy.context.scene
arm, body = bpy.data.objects["Rig"], bpy.data.objects["Settler"]

PX, F = p("frame_px", 24), p("supersample", 8)
ELEV = math.radians(p("elev_deg", 30))
TARGET_Z, DIST = p("target_z", 7.0), 60.0

# --- camera ---
cam_data = bpy.data.cameras.new("cam"); cam_data.type = "ORTHO"; cam_data.ortho_scale = PX
cam = bpy.data.objects.new("cam", cam_data); scn.collection.objects.link(cam)
cam.location = (p("cam_dx", 0.0), -DIST * math.cos(ELEV), TARGET_Z + DIST * math.sin(ELEV))
cam.rotation_euler = (math.pi / 2 - ELEV, 0, 0)
scn.camera = cam

# --- render settings: Cycles, 1 sample, no filtering, raw colors ---
r = scn.render
r.engine = "CYCLES"; scn.cycles.device = "CPU"; scn.cycles.samples = 1
scn.cycles.use_denoising = False; scn.cycles.pixel_filter_type = "BOX"; scn.cycles.filter_width = 0.01
scn.cycles.max_bounces = 0
r.resolution_x = r.resolution_y = PX * F; r.resolution_percentage = 100
r.film_transparent = True
r.image_settings.file_format = "PNG"; r.image_settings.color_mode = "RGBA"; r.image_settings.color_depth = "16"
scn.view_settings.view_transform = "Raw"; scn.view_settings.look = "None"
scn.display_settings.display_device = "sRGB"
try: scn.sequencer_colorspace_settings.name = "Non-Color"
except Exception: pass

# --- data material per part: replace materials by face part id ---
# part id from vertex group of the face's first vertex
ids = {"body": 1, "head": 2, "hand.L": 3, "hand.R": 4, "foot.L": 5, "foot.R": 6}
EYE_ID = 9
HAIR_ID = 7
def data_mat(pid):
    m = bpy.data.materials.new(f"id{pid}"); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    comb = nt.nodes.new("ShaderNodeCombineColor")
    cd = nt.nodes.new("ShaderNodeCameraData")
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    mr = nt.nodes.new("ShaderNodeMapRange")  # depth -> 0..1
    mr.inputs["From Min"].default_value = DIST - 20; mr.inputs["From Max"].default_value = DIST + 20
    mn = nt.nodes.new("ShaderNodeMapRange")  # normal z -> 0..1
    mn.inputs["From Min"].default_value = -1; mn.inputs["From Max"].default_value = 1
    nt.links.new(cd.outputs["View Z Depth"], mr.inputs["Value"])
    nt.links.new(geo.outputs["Normal"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Z"], mn.inputs["Value"])
    comb.inputs["Red"].default_value = pid / 16
    nt.links.new(mr.outputs["Result"], comb.inputs["Green"])
    nt.links.new(mn.outputs["Result"], comb.inputs["Blue"])
    nt.links.new(comb.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    return m

me = body.data
gname = {g.index: g.name for g in body.vertex_groups}
me.materials.clear()
slot_of = {}
for name, pid in list(ids.items()) + [("eye", EYE_ID), ("hair", HAIR_ID)]:
    me.materials.append(data_mat(pid)); slot_of[name] = len(me.materials) - 1
for poly in me.polygons:
    v = me.vertices[poly.vertices[0]]
    g = gname[max(v.groups, key=lambda x: x.weight).group]
    poly.material_index = slot_of[g]
# eyes share the "head" group; tag them by original material stored as custom attr
hair_faces = me.attributes.get("is_hair")
if hair_faces:
    for poly in me.polygons:
        if hair_faces.data[poly.index].value: poly.material_index = slot_of["hair"]
eye_faces = me.attributes.get("is_eye")
if eye_faces:
    for poly in me.polygons:
        if eye_faces.data[poly.index].value: poly.material_index = slot_of["eye"]

DIRS = ["S", "SW", "W", "NW", "N", "NE", "E", "SE"]
frames = p("render_frames", list(range(0, 16, 2)))
only_idle = p("only_idle", False)
ANIM = p("anim", "walk")
for di, dname in enumerate(DIRS):
    arm.rotation_euler = (0, 0, math.radians(-45 * di))
    if only_idle:
        arm.animation_data.action = None
        for b in arm.pose.bones: b.location = (0, 0, 0); b.rotation_euler = (0, 0, 0)
        scn.frame_set(0)
        r.filepath = f"{RAW}/idle_{di}_{dname}.png"; bpy.ops.render.render(write_still=True)
        continue
    for fi, f in enumerate(frames):
        scn.frame_set(f)
        r.filepath = f"{RAW}/{ANIM}_{di}_{dname}_{fi}.png"
        bpy.ops.render.render(write_still=True)
print("DONE")
