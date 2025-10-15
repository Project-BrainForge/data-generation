"""
Interactive 3D visualization of Region 1 on fsaverage5 cortex using PyVista.
Shows the entire cortex with region 1 highlighted in green.
"""
import pyvista as pv
import scipy.io
import numpy as np
import os

# Get script directory
base_dir = os.path.dirname(os.path.abspath(__file__))

# Load cortex and region mapping
cortex_path = os.path.join(base_dir, "fs_cortex_20k.mat")
region_map_path = os.path.join(base_dir, "fs_cortex_20k_region_mapping.mat")

print("Loading data...")
cortex = scipy.io.loadmat(cortex_path)
region_map = scipy.io.loadmat(region_map_path)

# Extract geometry
pos = cortex['pos']  # vertices (20484, 3)
tri = cortex['tri'] - 1  # faces, convert MATLAB 1-based to 0-based
rm = region_map['rm'].flatten()  # region mapping (20484,)

print(f"Loaded {pos.shape[0]} vertices, {tri.shape[0]} faces")
print(f"Unique regions: {len(np.unique(rm))}")

# Region to visualize
target_region = 20
region_mask = (rm == target_region)
num_verts_in_region = np.sum(region_mask)

print(f"\nRegion {target_region}:")
print(f"  Vertices: {num_verts_in_region}")
if num_verts_in_region > 0:
    centroid = pos[region_mask].mean(axis=0)
    print(f"  Centroid: [{centroid[0]:.2f}, {centroid[1]:.2f}, {centroid[2]:.2f}]")

# Create mesh
faces_with_count = np.hstack([np.full((tri.shape[0], 1), 3), tri]).astype(np.int32)
mesh = pv.PolyData(pos, faces_with_count)

# Create scalar array: 0 for background, 1 for target region
region_highlight = np.where(region_mask, 1.0, 0.0)
mesh["RegionHighlight"] = region_highlight

# Set up plotter
plotter = pv.Plotter(window_size=[1200, 900])

# Add mesh with custom colormap (gray to green)
plotter.add_mesh(
    mesh,
    scalars="RegionHighlight",
    cmap=['white', 'green'],  # 0 -> gray, 1 -> green
    show_scalar_bar=False,
    opacity=0.95,
    lighting=True,
    smooth_shading=True
)

# Add title
plotter.add_title(
    f"fsaverage5 Cortex - Region {target_region} (green)\n{num_verts_in_region} vertices",
    font_size=12
)

# Set camera view (similar to MATLAB view angle)
plotter.camera_position = 'xy'
plotter.camera.azimuth = 40
plotter.camera.elevation = 20

# Add interactive controls info
plotter.add_text(
    "Controls:\n"
    "  Left click + drag: Rotate\n"
    "  Scroll: Zoom\n"
    "  Middle click + drag: Pan\n"
    "  'q': Quit\n"
    "  's': Screenshot (saves to image.png)",
    position='lower_left',
    font_size=8,
    color='white'
)

print("\n🖼️  Opening interactive 3D viewer...")
print("Close window or press 'q' to exit")

# Show interactive plot
plotter.show()
