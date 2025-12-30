"""
Blender render automation for Rashguard mockup.
Loads pattern images and renders using Camera.001
"""

import bpy
import os
import sys

# Configuration
PATTERN_NAME = "CONGO.png"  # Filename in /patterns/ folder
PATTERN_BASE = "CONGO"  # Pattern name without extension (for output files)
OUTPUT_DIR = "/output"
CAMERA_NAME = "1. Camera (close front)"  # Active camera in your scene
RASHGUARD_OBJECT = "Rashguard"  # The mesh object with 7 material slots
BLEND_FILE = "Rashguard mockup.blend"
RENDER_ENGINE = "CYCLES"
RENDER_SAMPLES = 32
RESOLUTION_SCALE = 50
OUTPUT_WIDTH = 500
OUTPUT_HEIGHT = 500
PRESETS = [['1. Camera (close front)', 0]]
CAMERAS_TO_RENDER = ('1. Camera (close front)',)
THREADS_COLOR = "#007FFF"

def load_pattern(image_filename):
    """Load image from patterns folder."""
    # Get the script directory and build patterns path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    patterns_dir = os.path.join(script_dir, "patterns")
    image_path = os.path.join(patterns_dir, image_filename)
    
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Pattern not found: {image_path}\nPlease place '{image_filename}' in the patterns/ folder")
    
    img = bpy.data.images.load(image_path, check_existing=True)
    print(f"✓ Loaded pattern from: {image_path}")
    return img

def assign_pattern_to_rashguard_materials(image):
    """
    Assign the same image to all TEX_IMAGE nodes in the rashguard object's materials.
    This ensures all 7 material slots use the same pattern.
    """
    updated_count = 0
    
    obj = bpy.data.objects.get(RASHGUARD_OBJECT)
    if not obj:
        raise ValueError(f"Object '{RASHGUARD_OBJECT}' not found")
    
    # Loop through all material slots on the rashguard
    for slot in obj.material_slots:
        mat = slot.material
        if not mat or not mat.use_nodes:
            continue
        
        # Update all Image Texture nodes in this material
        for node in mat.node_tree.nodes:
            if node.type == 'TEX_IMAGE':
                node.image = image
                updated_count += 1
    
    print(f"✓ Updated {updated_count} image texture nodes in rashguard materials")
    return updated_count

def apply_threads_color(color_hex):
    """Apply color to threads material slots (8-12) only."""
    if not color_hex or color_hex == 'None':
        print("ℹ️  No threads color specified, skipping")
        return
    
    try:
        hex_str = str(color_hex).lstrip('#')
        r = int(hex_str[0:2], 16) / 255.0
        g = int(hex_str[2:4], 16) / 255.0
        b = int(hex_str[4:6], 16) / 255.0
        color_rgba = (r, g, b, 1.0)
    except Exception as e:
        print(f"✗ ERROR: Convert color failed: {e}")
        return
    
    obj = bpy.data.objects.get(RASHGUARD_OBJECT)
    if not obj:
        print(f"✗ ERROR: Object '{RASHGUARD_OBJECT}' not found")
        return
    
    updated_count = 0
    # Only process slots 8-12 (0-indexed: 7-11) for threads
    for idx in range(7, min(12, len(obj.material_slots))):
        slot = obj.material_slots[idx]
        mat = slot.material
        if not mat:
            continue
        
        if not mat.use_nodes:
            mat.use_nodes = True
        
        # Check all nodes in the material
        for node in mat.node_tree.nodes:
            # Try GROUP nodes first (they expose inputs)
            if node.type == 'GROUP':
                # Check if GROUP has Color input
                if 'Color' in node.inputs:
                    try:
                        node.inputs['Color'].default_value = color_rgba
                        updated_count += 1
                        print(f"   Thread slot {idx+1}: Updated GROUP '{node.name}' Color")
                    except Exception as e:
                        print(f"   Thread slot {idx+1}: Failed to update GROUP Color - {e}")
                
                # Also check inside GROUP for nodes with Color input
                if node.node_tree:
                    for sub_node in node.node_tree.nodes:
                        if 'Color' in sub_node.inputs:
                            try:
                                sub_node.inputs['Color'].default_value = color_rgba
                                updated_count += 1
                                print(f"   Thread slot {idx+1}: Updated '{sub_node.name}' Color inside GROUP")
                            except Exception as e:
                                print(f"   Thread slot {idx+1}: Failed - {e}")
            
            # Try direct nodes with Color input
            else:
                if 'Color' in node.inputs:
                    try:
                        node.inputs['Color'].default_value = color_rgba
                        updated_count += 1
                        print(f"   Thread slot {idx+1}: Updated '{node.name}' Color")
                    except Exception as e:
                        print(f"   Thread slot {idx+1}: Failed - {e}")
    
    print(f"✓ Applied threads color ({color_hex}) to {updated_count} thread Color inputs (slots 8-12)")
    return updated_count

def get_all_cameras():
    """Get all camera objects in the scene."""
    cameras = [obj for obj in bpy.data.objects if obj.type == 'CAMERA']
    return cameras

def render_presets(output_dir, pattern_name):
    """
    Render multiple presets: list of [camera, frame] pairs.
    """
    if not PRESETS:
        return
    
    print(f"\n🎬 PRESET RENDER MODE")
    print(f"   Total presets: {len(PRESETS)}")
    
    # Get all cameras once
    all_cameras = get_all_cameras()
    camera_dict = {cam.name: cam for cam in all_cameras}
    
    for preset_idx, (camera_name, frame_num) in enumerate(PRESETS, 1):
        print(f"\n   [{preset_idx}/{len(PRESETS)}] {camera_name} @ frame {frame_num}")
        
        # Find the preset camera
        if camera_name not in camera_dict:
            print(f"   ✗ Camera '{camera_name}' not found, skipping")
            continue
        
        preset_cam = camera_dict[camera_name]
        
        # Set scene and camera
        scene = bpy.context.scene
        scene.camera = preset_cam
        scene.frame_set(frame_num)
        
        # Apply resolution scaling
        if RESOLUTION_SCALE < 50:
            final_width = int(OUTPUT_WIDTH * RESOLUTION_SCALE / 50)
            final_height = int(OUTPUT_HEIGHT * RESOLUTION_SCALE / 50)
        else:
            final_width = OUTPUT_WIDTH
            final_height = OUTPUT_HEIGHT
        
        # Create output filename with pattern name prefix
        safe_pattern = PATTERN_BASE.replace(" ", "_").replace(".", "_").replace("(", "").replace(")", "")
        safe_camera = preset_cam.name.replace(" ", "_").replace(".", "_")
        output_file = os.path.join(output_dir, f"{safe_pattern}_f{frame_num}_{safe_camera}.png")
        
        # Configure render
        scene.render.engine = RENDER_ENGINE
        scene.render.filepath = output_file
        scene.render.image_settings.file_format = 'PNG'
        scene.render.image_settings.color_mode = 'RGBA'
        scene.render.resolution_x = final_width
        scene.render.resolution_y = final_height
        
        # Engine-specific settings
        if RENDER_ENGINE == 'CYCLES':
            scene.cycles.samples = RENDER_SAMPLES
            scene.cycles.use_denoising = True
        elif RENDER_ENGINE == 'BLENDER_EEVEE_NEXT':
            scene.eevee.taa_render_samples = RENDER_SAMPLES
        
        print(f"                    -> {output_file} ({final_width}x{final_height})", flush=True)
        sys.stdout.flush()
        
        # Render
        bpy.ops.render.render(write_still=True)
        
        print(f"                    ✓ COMPLETE", flush=True)
        sys.stdout.flush()
    
    print(f"\n✓ All {len(PRESETS)} presets rendered!")

def render_all_cameras(output_dir):
    """
    Render the scene with each camera.
    Creates a numbered output file for each camera.
    """
    # Get all cameras from scene
    all_cameras = get_all_cameras()
    
    # Filter to only render selected cameras
    if CAMERAS_TO_RENDER:
        cameras = [cam for cam in all_cameras if cam.name in CAMERAS_TO_RENDER]
    else:
        cameras = all_cameras
    
    if not cameras:
        raise ValueError("No cameras found in the scene or invalid camera selection")
    
    print(f"\n📹 Found {len(cameras)} cameras:")
    for i, cam in enumerate(cameras, 1):
        print(f"   {i}. {cam.name}")
    
    print(f"\n🎬 Starting render sequence...")
    print(f"   Engine: {RENDER_ENGINE}")
    print(f"   Resolution: {RESOLUTION_SCALE}%")
    print(f"   Output Size: {OUTPUT_WIDTH}x{OUTPUT_HEIGHT}px")
    
    # Get base resolution and apply scaling
    scene = bpy.context.scene
    
    # Use output dimensions directly (applies resolution scale if needed)
    if RESOLUTION_SCALE < 50:
        final_width = int(OUTPUT_WIDTH * RESOLUTION_SCALE / 50)
        final_height = int(OUTPUT_HEIGHT * RESOLUTION_SCALE / 50)
    else:
        final_width = OUTPUT_WIDTH
        final_height = OUTPUT_HEIGHT
    
    for i, cam in enumerate(cameras, 1):
        # Set this camera as active
        bpy.context.scene.camera = cam
        
        # Create output filename based on camera name
        safe_name = cam.name.replace(" ", "_").replace(".", "_")
        output_file = os.path.join(output_dir, f"{i:02d}_{safe_name}.png")
        
        # Configure render
        scene = bpy.context.scene
        scene.render.engine = RENDER_ENGINE
        scene.render.filepath = output_file
        scene.render.image_settings.file_format = 'PNG'
        scene.render.image_settings.color_mode = 'RGBA'
        
        # Set resolution
        scene.render.resolution_x = final_width
        scene.render.resolution_y = final_height
        
        # Engine-specific settings
        if RENDER_ENGINE == 'CYCLES':
            scene.cycles.samples = RENDER_SAMPLES  # Cycles quality
            scene.cycles.use_denoising = True
        elif RENDER_ENGINE == 'BLENDER_EEVEE_NEXT':
            scene.eevee.taa_render_samples = RENDER_SAMPLES  # EEVEE quality
        
        # Output progress markers
        progress_line = f"[{i}/{len(cameras)}] Rendering: {cam.name}"
        print(progress_line, flush=True)
        sys.stdout.flush()
        print(f"              -> {output_file} ({final_width}x{final_height})", flush=True)
        sys.stdout.flush()
        
        # Render
        bpy.ops.render.render(write_still=True)
        
        # Output completion marker
        complete_line = f"              COMPLETE"
        print(complete_line, flush=True)
        sys.stdout.flush()
    
    print(f"\n✓ All {len(cameras)} renders complete!")

def main():
    """Main workflow."""
    print("=" * 50)
    print("RASHGUARD RENDER AUTOMATION")
    print("=" * 50)
    
    try:
        # Load pattern image
        pattern_image = load_pattern(PATTERN_NAME)
        
        # Assign to rashguard materials only
        assign_pattern_to_rashguard_materials(pattern_image)
        
        # Apply thread color (already extracted in render_cli.py and passed via THREADS_COLOR)
        apply_threads_color(THREADS_COLOR)
        
        # Setup output directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_dir = os.path.join(script_dir, "output")
        os.makedirs(output_dir, exist_ok=True)
        
        # Render presets or all cameras
        if PRESETS:
            render_presets(output_dir, PATTERN_NAME)
        else:
            render_all_cameras(output_dir)
        
        print("\n✓ SUCCESS!")
        print(f"Renders saved to: {output_dir}")
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
