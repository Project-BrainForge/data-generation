# Python
import numpy as np
from scipy.io import loadmat
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import os

base = r"d:\Deep sif\Data Generation\data-generation\anatomy"
rm_mat = loadmat(os.path.join(base, "fs_cortex_20k_region_mapping.mat"))
cortex = loadmat(os.path.join(base, "fs_cortex_20k.mat"))

# load region mapping (1 x 20484 matlab -> flatten)
rm = np.squeeze(rm_mat['rm'])
if rm.ndim > 1:
    rm = rm.ravel()

# load vertex positions (pos may be (3, N) or (N, 3))
pos = cortex.get('pos', None)
if pos is None:
    # try alternative keys
    pos = cortex.get('posl', None)  # fallback
if pos is None:
    raise RuntimeError("Could not find 'pos' in fs_cortex_20k.mat")

pos = np.array(pos)
if pos.shape[0] == 3 and pos.shape[1] != 3:
    pos = pos.T  # make (N,3)

N = pos.shape[0]
print("Total vertices (pos):", N)
print("rm length:", rm.size)

# load hemisphere indices and convert from MATLAB 1-based if needed
left_ind = cortex.get('left_ind', None)
right_ind = cortex.get('right_ind', None)
if left_ind is None or right_ind is None:
    raise RuntimeError("left_ind/right_ind not found in fs_cortex_20k.mat")

left_ind = np.squeeze(left_ind).astype(int)
right_ind = np.squeeze(right_ind).astype(int)

# convert to 0-based if indices look 1-based
if left_ind.min() == 1:
    left_ind = left_ind - 1
if right_ind.min() == 1:
    right_ind = right_ind - 1

# region id to inspect
region_id = 990
verts_in_region = np.where(rm == region_id)[0]
print(f"Region {region_id} -> total vertices:", verts_in_region.size)

verts_left = np.intersect1d(verts_in_region, left_ind)
verts_right = np.intersect1d(verts_in_region, right_ind)
print("  left hemisphere verts:", verts_left.size)
print("  right hemisphere verts:", verts_right.size)

# centroid
if verts_in_region.size:
    centroid = pos[verts_in_region].mean(axis=0)
    print("  centroid (x,y,z):", centroid)
else:
    print("  region has zero vertices")

# Quick 3D plot: all verts light gray, region verts red
fig = plt.figure(figsize=(8,6))
ax = fig.add_subplot(111, projection='3d')
ax.scatter(pos[:,0], pos[:,1], pos[:,2], s=1, c='lightgray', alpha=0.4)
if verts_in_region.size:
    ax.scatter(pos[verts_in_region,0], pos[verts_in_region,1], pos[verts_in_region,2],
               s=6, c='red', label=f"region {region_id}")
ax.set_axis_off()
ax.view_init(elev=20, azim=40)
ax.legend()
outf = os.path.join(base, f"region_{region_id}_preview.png")
plt.savefig(outf, dpi=150, bbox_inches='tight')
print("Saved preview to:", outf)