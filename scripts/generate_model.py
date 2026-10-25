"""Generate the original Arc assembly GLB. No third-party models or textures."""
from pathlib import Path
import math
import numpy as np
import trimesh
from trimesh.visual.material import PBRMaterial
ROOT=Path(__file__).resolve().parents[1]
SILVER=PBRMaterial(name='brushed-silver',baseColorFactor=[0.79,0.81,0.85,1],metallicFactor=0.88,roughnessFactor=0.23)
DARK=PBRMaterial(name='graphite-ceramic',baseColorFactor=[0.06,0.065,0.08,1],metallicFactor=0.35,roughnessFactor=0.32)
LIGHT=PBRMaterial(name='porcelain-silver',baseColorFactor=[0.92,0.93,0.95,1],metallicFactor=0.5,roughnessFactor=0.25)

def bevel_box(extents,radius=0.1):
    half=np.array(extents)/2-radius
    unit=trimesh.creation.icosphere(subdivisions=1,radius=radius).vertices
    corners=np.array([[x,y,z] for x in (-half[0],half[0]) for y in (-half[1],half[1]) for z in (-half[2],half[2])])
    return trimesh.convex.convex_hull(np.vstack([unit+c for c in corners]))

def arc(radius,tube,start,end,steps=80,sides=10):
    angles=np.linspace(start,end,steps);around=np.linspace(0,2*np.pi,sides,endpoint=False)
    vertices=[]
    for a in angles:
        for b in around:vertices.append([(radius+tube*np.cos(b))*np.cos(a),tube*np.sin(b),(radius+tube*np.cos(b))*np.sin(a)])
    faces=[]
    for i in range(steps-1):
        for j in range(sides):
            a=i*sides+j;b=i*sides+(j+1)%sides;c=(i+1)*sides+j;d=(i+1)*sides+(j+1)%sides
            faces.extend([[a,c,b],[b,c,d]])
    mesh=trimesh.Trimesh(vertices=vertices,faces=faces);mesh.fix_normals();return mesh

def add(scene,mesh,name,position=(0,0,0),rotation=None,material=SILVER):
    mesh.visual=trimesh.visual.TextureVisuals(material=material)
    T=np.eye(4)
    if rotation is not None:T=trimesh.transformations.euler_matrix(*rotation)
    T[:3,3]=position
    scene.add_geometry(mesh,node_name=name,geom_name=name,transform=T)

def build():
    scene=trimesh.Scene()
    # Three individually addressable layers and their clean inset rails.
    for i,y in enumerate((-0.54,0,0.54)):
        add(scene,bevel_box([1.62,0.34,1.62],0.1),f'Processing_layer_{i}',(0,y,0),rotation=(0,math.pi/4,0),material=SILVER)
        add(scene,bevel_box([1.18,0.08,1.18],0.035),f'Core_insert_{i}',(0,y+0.2,0),rotation=(0,math.pi/4,0),material=DARK)
    add(scene,bevel_box([0.55,0.1,0.55],0.035),'Result_top',(0,0.81,0),rotation=(0,math.pi/4,0),material=LIGHT)
    for i,(r,a,b,rot) in enumerate([(2.35,-0.3,4.9,(0.36,0,0.12)),(2.0,0.2,5.8,(1.15,0.3,-0.4))]):
        add(scene,arc(r,0.024,a,b),f'Connection_orbit_{i}',rotation=rot)
    satellites=[('Input',(-2.05,0.45,0.65)),('Security',(1.95,0.9,-0.55)),('Events',(-0.7,-0.9,-1.95)),('Result',(1.55,-0.62,1.5))]
    for i,(name,pos) in enumerate(satellites):
        add(scene,bevel_box([0.66,0.24,0.66],0.075),name+'_module',pos,rotation=(0.2,i*0.55,0.08),material=LIGHT)
        add(scene,bevel_box([0.3,0.07,0.3],0.025),name+'_inset',np.array(pos)+[0,0.16,0],rotation=(0.2,i*0.55,0.08),material=DARK)
    add(scene,trimesh.creation.icosphere(subdivisions=2,radius=0.075),'Connection_packet',(0.2,0.22,2.31),material=LIGHT)
    return scene
if __name__=='__main__':
    path=ROOT/'apps/website/public/models/arc-assembly.glb';path.parent.mkdir(parents=True,exist_ok=True)
    scene=build();path.write_bytes(scene.export(file_type='glb'))
    loaded=trimesh.load(path,force='scene')
    assert len(loaded.geometry)==len(scene.geometry)
    assert all(np.isfinite(g.vertices).all() for g in loaded.geometry.values())
    triangles=sum(len(g.faces) for g in loaded.geometry.values())
    print(f'{path.name}: {path.stat().st_size:,} bytes; {len(loaded.geometry)} meshes; {triangles:,} triangles; round-trip verified')
