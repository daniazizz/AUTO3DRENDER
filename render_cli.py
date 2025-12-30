#!/usr/bin/env python3
"""
Command-line renderer for Rashguard mockup.
Reads configuration from config.json and executes Blender render.
Supports rendering all patterns in the patterns folder.
"""

import json
import sys
import os
import subprocess
import argparse
from pathlib import Path
from PIL import Image
from collections import Counter

def extract_thread_color_from_pattern(pattern_path):
    """
    Extract thread color from top-right corner of pattern image using PIL.
    Returns hex color string (e.g., "#0283EC").
    """
    pil_image = Image.open(pattern_path)
    pil_image = pil_image.convert("RGBA")  # Ensure RGBA format
    
    # Get image dimensions
    width, height = pil_image.size
    
    # Sample region: top-right area with margin
    # Start from (90% width, 5% height) to (100% width, 15% height)
    sample_width = max(1, int(width * 0.1))
    sample_height = max(1, int(height * 0.05))
    start_x = max(0, int(width * 0.9))
    start_y = max(0, int(height * 0.05))  # 5% down from top
    
    # Collect colors from the region
    colors = []
    
    for sy in range(sample_height):
        for sx in range(sample_width):
            x = start_x + sx
            y = start_y + sy
            
            # Get pixel color
            pixel = pil_image.getpixel((x, y))
            r, g, b, a = pixel[0], pixel[1], pixel[2], pixel[3]
            
            # Skip transparent pixels
            if a > 200:
                colors.append((r, g, b))
    
    # Use most common color from region
    if colors:
        most_common = Counter(colors).most_common(1)[0][0]
        hex_color = f"#{most_common[0]:02X}{most_common[1]:02X}{most_common[2]:02X}"
    else:
        # Fallback to single pixel slightly offset from corner
        x = min(width - 1, start_x)
        y = start_y
        pixel = pil_image.getpixel((x, y))
        r, g, b = pixel[0], pixel[1], pixel[2]
        hex_color = f"#{r:02X}{g:02X}{b:02X}"
    
    return hex_color

def load_config(config_path):
    """Load configuration from JSON file."""
    with open(config_path, 'r') as f:
        return json.load(f)

def save_config(config_path, config):
    """Save configuration to JSON file."""
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)

def main():
    parser = argparse.ArgumentParser(
        description='Rashguard Render Automation - CLI Version',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python render_cli.py                          # Render all patterns
  python render_cli.py --config myconfig.json   # Use custom config
  python render_cli.py --color "#FF0000"        # Set thread color (red)
  python render_cli.py --preset "Camera.001" 180 "Camera.002" 240  # Multiple presets
  python render_cli.py --cameras "Camera1" "Camera2"  # Select cameras
        '''
    )
    
    parser.add_argument('--config', default='config.json', help='Config file path (default: config.json)')
    parser.add_argument('--samples', type=int, help='Render samples (8-256)')
    parser.add_argument('--engine', choices=['CYCLES', 'EEVEE'], help='Render engine')
    parser.add_argument('--resolution', type=int, choices=[50, 75, 100], help='Resolution scale (%)')
    parser.add_argument('--width', type=int, help='Output image width (pixels)')
    parser.add_argument('--height', type=int, help='Output image height (pixels)')
    parser.add_argument('--color', '--threads-color', dest='threads_color', help='Thread color (hex: #RRGGBB)')
    parser.add_argument('--preset', nargs='+', metavar='ARGS', help='Render presets: pairs of camera name and frame (e.g., "Camera.001" 180 "Camera.002" 240)')
    parser.add_argument('--cameras', nargs='+', help='Camera names to render')
    parser.add_argument('--output', help='Output directory')
    parser.add_argument('--list-cameras', action='store_true', help='List available cameras and exit')
    parser.add_argument('--list-patterns', action='store_true', help='List available patterns and exit')
    
    args = parser.parse_args()
    
    # Load base config
    if not os.path.exists(args.config):
        print(f"Error: Config file '{args.config}' not found")
        sys.exit(1)
    
    config = load_config(args.config)
    
    # Override with command-line arguments
    if args.samples:
        config['samples'] = args.samples
    if args.engine:
        config['engine'] = args.engine
    if args.resolution:
        config['resolution_scale'] = args.resolution
    if args.width:
        config['output_width'] = args.width
    if args.height:
        config['output_height'] = args.height
    if args.threads_color:
        config['threads_color'] = args.threads_color
    if args.preset:
        # Parse preset pairs: ["camera1", "180", "camera2", "240"] -> [["camera1", 180], ["camera2", 240]]
        presets = []
        for i in range(0, len(args.preset), 2):
            if i + 1 < len(args.preset):
                camera_name = args.preset[i]
                frame_num = int(args.preset[i + 1])
                presets.append([camera_name, frame_num])
        config['presets'] = presets
    if args.cameras:
        config['cameras'] = args.cameras
    if args.output:
        config['output_dir'] = args.output
    
    patterns_dir = Path('patterns')
    
    # Handle --list-patterns
    if args.list_patterns:
        if patterns_dir.exists():
            patterns = sorted([f.name for f in patterns_dir.glob('*.png')])
            if patterns:
                print("Available patterns:")
                for p in patterns:
                    print(f"  - {p}")
            else:
                print("No patterns found")
        else:
            print("Patterns directory not found")
        return
    
    if args.list_cameras:
        print("To see available cameras, render with verbose output")
        return
    
    # Always render all patterns in patterns folder
    if patterns_dir.exists():
        patterns_to_render = sorted([f.name for f in patterns_dir.glob('*.png')])
        if not patterns_to_render:
            print(f"Error: No PNG files found in {patterns_dir}/")
            sys.exit(1)
    else:
        print(f"Error: Patterns directory not found: {patterns_dir}/")
        sys.exit(1)
    
    # Validate patterns exist
    for pattern_name in patterns_to_render:
        pattern_path = patterns_dir / pattern_name
        if not pattern_path.exists():
            print(f"Error: Pattern not found: {pattern_path}")
            sys.exit(1)
    
    print("=" * 60)
    print("RASHGUARD RENDER AUTOMATION - CLI")
    print("=" * 60)
    print(f"Will render {len(patterns_to_render)} pattern(s):")
    for p in patterns_to_render:
        print(f"  - {p}")
    print()
    
    # Map engine names
    engine_map = {
        'CYCLES': 'CYCLES',
        'EEVEE': 'BLENDER_EEVEE_NEXT'
    }
    blender_engine = engine_map.get(config['engine'], 'CYCLES')
    
    # Find Blender executable
    blender_paths = [
        Path('C:/Program Files/Blender Foundation/Blender 4.5/blender.exe'),
        Path('/Applications/Blender.app/Contents/MacOS/Blender'),
        Path('/usr/bin/blender'),
        Path('/snap/bin/blender'),
    ]
    
    blender_exe = None
    for path in blender_paths:
        if path.exists():
            blender_exe = path
            break
    
    if not blender_exe:
        print("Error: Blender executable not found. Please install Blender.")
        sys.exit(1)
    
    # Get blend file
    blend_file = Path(config['blend_file'])
    if not blend_file.exists():
        print(f"Error: Blend file not found: {blend_file}")
        sys.exit(1)
    
    # Render each pattern
    render_script_path = Path('render_rashguard.py')
    original_script_content = None
    temp_script = Path('.render_temp.py')
    
    try:
        for pattern_name in patterns_to_render:
            print("=" * 60)
            print(f"RENDERING: {pattern_name}")
            print("=" * 60)
            
            # Load original script content once
            if original_script_content is None:
                with open(render_script_path, 'r', encoding='utf-8') as f:
                    original_script_content = f.read()
            
            script_content = original_script_content
            
            # Replace placeholders for this pattern
            cameras_str = repr(tuple(config.get('cameras', [])))
            
            # Extract thread color from pattern using PIL
            pattern_path = patterns_dir / pattern_name
            thread_color = extract_thread_color_from_pattern(str(pattern_path))
            print(f"  Extracted thread color: {thread_color}")
            
            presets = config.get('presets', [])
            presets_str = repr(presets)
            
            # Remove file extension for cleaner output names
            pattern_base = os.path.splitext(pattern_name)[0]
            script_content = script_content.replace('__PATTERN_PLACEHOLDER__', pattern_name)
            script_content = script_content.replace('__PATTERN_BASE_PLACEHOLDER__', pattern_base)
            script_content = script_content.replace('__ENGINE_PLACEHOLDER__', blender_engine)
            script_content = script_content.replace('__SAMPLES_PLACEHOLDER__', str(config['samples']))
            script_content = script_content.replace('__SCALE_PLACEHOLDER__', str(config['resolution_scale']))
            script_content = script_content.replace('__OUTPUT_WIDTH_PLACEHOLDER__', str(config.get('output_width', 480)))
            script_content = script_content.replace('__OUTPUT_HEIGHT_PLACEHOLDER__', str(config.get('output_height', 480)))
            script_content = script_content.replace('__PRESETS_PLACEHOLDER__', presets_str)
            script_content = script_content.replace('__CAMERAS_PLACEHOLDER__', cameras_str)
            script_content = script_content.replace('__THREADS_COLOR_PLACEHOLDER__', thread_color)
            
            # Write temp script
            with open(temp_script, 'w', encoding='utf-8') as f:
                f.write(script_content)
            
            # Print pattern info
            print(f"Pattern:         {pattern_name}")
            print(f"Samples:         {config['samples']}")
            print(f"Engine:          {config['engine']}")
            print(f"Resolution:      {config['resolution_scale']}%")
            print(f"Output Size:     {config.get('output_width', 480)}x{config.get('output_height', 480)}px")
            print(f"Output Dir:      {config['output_dir']}")
            print()
            
            # Run Blender for this pattern
            print(f"Starting Blender render...")
            print()
            
            env = os.environ.copy()
            env['PYTHONUNBUFFERED'] = '1'
            
            result = subprocess.run(
                [str(blender_exe), str(blend_file), '--background', '--python', str(temp_script)],
                env=env,
                cwd=os.getcwd()
            )
            
            if result.returncode == 0:
                print()
                print(f"✓ {pattern_name} render complete!")
                print()
            else:
                print()
                print(f"✗ {pattern_name} render failed")
                print()
    
    finally:
        # Clean up temp script
        if temp_script.exists():
            temp_script.unlink()
        
        # Restore placeholders in original script
        if original_script_content:
            with open(render_script_path, 'w', encoding='utf-8') as f:
                f.write(original_script_content)
    
    print("=" * 60)
    print(f"✓ ALL {len(patterns_to_render)} PATTERNS RENDERED!")
    print("=" * 60)
    print(f"Output saved to: {config['output_dir']}/")

if __name__ == '__main__':
    main()

def load_config(config_path):
    """Load configuration from JSON file."""
    with open(config_path, 'r') as f:
        return json.load(f)

def save_config(config_path, config):
    """Save configuration to JSON file."""
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)

def main():
    parser = argparse.ArgumentParser(
        description='Rashguard Render Automation - CLI Version',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python render_cli.py                          # Use config.json
  python render_cli.py --config myconfig.json   # Use custom config
  python render_cli.py --pattern mypattern.png  # Override pattern
  python render_cli.py --color "#FF0000"        # Set thread color (red)
  python render_cli.py --preset "Camera.001" 180 "Camera.002" 240  # Multiple presets
  python render_cli.py --cameras "Camera1" "Camera2"  # Select cameras
        '''
    )
    
    parser.add_argument('--config', default='config.json', help='Config file path (default: config.json)')
    parser.add_argument('--pattern', help='Pattern image filename')
    parser.add_argument('--samples', type=int, help='Render samples (8-256)')
    parser.add_argument('--engine', choices=['CYCLES', 'EEVEE'], help='Render engine')
    parser.add_argument('--resolution', type=int, choices=[50, 75, 100], help='Resolution scale (%)')
    parser.add_argument('--width', type=int, help='Output image width (pixels)')
    parser.add_argument('--height', type=int, help='Output image height (pixels)')
    parser.add_argument('--color', '--threads-color', dest='threads_color', help='Thread color (hex: #RRGGBB)')
    parser.add_argument('--preset', nargs='+', metavar='ARGS', help='Render presets: pairs of camera name and frame (e.g., "Camera.001" 180 "Camera.002" 240)')
    parser.add_argument('--cameras', nargs='+', help='Camera names to render')
    parser.add_argument('--output', help='Output directory')
    parser.add_argument('--list-cameras', action='store_true', help='List available cameras and exit')
    parser.add_argument('--list-patterns', action='store_true', help='List available patterns and exit')
    
    args = parser.parse_args()
    
    # Load base config
    if not os.path.exists(args.config):
        print(f"Error: Config file '{args.config}' not found")
        sys.exit(1)
    
    config = load_config(args.config)
    
    # Override with command-line arguments
    if args.samples:
        config['samples'] = args.samples
    if args.engine:
        config['engine'] = args.engine
    if args.resolution:
        config['resolution_scale'] = args.resolution
    if args.width:
        config['output_width'] = args.width
    if args.height:
        config['output_height'] = args.height
    if args.threads_color:
        config['threads_color'] = args.threads_color
    if args.preset:
        # Parse preset pairs: ["camera1", "180", "camera2", "240"] -> [["camera1", 180], ["camera2", 240]]
        presets = []
        for i in range(0, len(args.preset), 2):
            if i + 1 < len(args.preset):
                try:
                    presets.append([args.preset[i], int(args.preset[i+1])])
                except ValueError:
                    print(f"Error: Frame must be a number, got '{args.preset[i+1]}'")
                    sys.exit(1)
        if presets:
            config['presets'] = presets
    if args.cameras:
        config['cameras'] = args.cameras
    if args.output:
        config['output_dir'] = args.output
    
    # Handle list commands
    if args.list_patterns:
        patterns_dir = Path('patterns')
        if patterns_dir.exists():
            patterns = sorted([f.name for f in patterns_dir.glob('*') if f.is_file()])
            print("Available patterns:")
            for p in patterns:
                print(f"  - {p}")
        else:
            print("Patterns directory not found")
        return
    
    if args.list_cameras:
        # Would need to open Blender and query scenes - for now show message
        print("To see available cameras, render with verbose output")
        return
    
    # Validate config
    if not config.get('pattern'):
        print("Error: No pattern specified. Use --pattern or set in config.json")
        sys.exit(1)
    
    patterns_dir = Path('patterns')
    
    # Render all patterns in the folder
    patterns_to_render = []
    # Get all PNG files from patterns folder
    if patterns_dir.exists():
        patterns_to_render = sorted([f.name for f in patterns_dir.glob('*.png')])
        if not patterns_to_render:
            print(f"Error: No PNG files found in {patterns_dir}/")
            sys.exit(1)
    else:
        print(f"Error: Patterns directory not found: {patterns_dir}/")
        sys.exit(1)
    
    print(f"Will render {len(patterns_to_render)} pattern(s):")
    for p in patterns_to_render:
        print(f"  - {p}")
    print()
    
    # Map engine names
    engine_map = {
        'CYCLES': 'CYCLES',
        'EEVEE': 'BLENDER_EEVEE_NEXT'
    }
    blender_engine = engine_map.get(config['engine'], 'CYCLES')
    
    # Find Blender executable
    blender_paths = [
        Path('C:/Program Files/Blender Foundation/Blender 4.5/blender.exe'),
        Path('/Applications/Blender.app/Contents/MacOS/Blender'),
        Path('/usr/bin/blender'),
        Path('/snap/bin/blender'),
    ]
    
    blender_exe = None
    for path in blender_paths:
        if path.exists():
            blender_exe = path
            break
    
    if not blender_exe:
        print("Error: Blender executable not found. Please install Blender.")
        sys.exit(1)
    
    # Get blend file
    blend_file = Path(config['blend_file'])
    if not blend_file.exists():
        print(f"Error: Blend file not found: {blend_file}")
        sys.exit(1)
    
    # Render each pattern
    render_script_path = Path('render_rashguard.py')
    original_script_content = None
    
    for pattern_name in patterns_to_render:
        print("=" * 60)
        print(f"RENDERING: {pattern_name}")
        print("=" * 60)
    
    # Replace placeholders
    cameras_str = repr(tuple(config.get('cameras', [])))
    color_replacement = config.get('threads_color', '')  # No extra quotes - placeholder is already in quotes
    presets = config.get('presets', [])
    presets_str = repr(presets)
    
    script_content = script_content.replace('__PATTERN_PLACEHOLDER__', config['pattern'])
    script_content = script_content.replace('__ENGINE_PLACEHOLDER__', blender_engine)
    script_content = script_content.replace('__SAMPLES_PLACEHOLDER__', str(config['samples']))
    script_content = script_content.replace('__SCALE_PLACEHOLDER__', str(config['resolution_scale']))
    script_content = script_content.replace('__OUTPUT_WIDTH_PLACEHOLDER__', str(config.get('output_width', 480)))
    script_content = script_content.replace('__OUTPUT_HEIGHT_PLACEHOLDER__', str(config.get('output_height', 480)))
    script_content = script_content.replace('__PRESETS_PLACEHOLDER__', presets_str)
    script_content = script_content.replace('__CAMERAS_PLACEHOLDER__', cameras_str)
    script_content = script_content.replace('__THREADS_COLOR_PLACEHOLDER__', color_replacement)
    
    # Write temp script
    temp_script = Path('.render_temp.py')
    with open(temp_script, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    # Print configuration
    print("=" * 60)
    print("RASHGUARD RENDER AUTOMATION - CLI")
    print("=" * 60)
    print(f"Pattern:         {config['pattern']}")
    print(f"Samples:         {config['samples']}")
    print(f"Engine:          {config['engine']}")
    print(f"Resolution:      {config['resolution_scale']}%")
    print(f"Output Size:     {config.get('output_width', 480)}x{config.get('output_height', 480)}px")
    print(f"Thread Color:    {config.get('threads_color', 'white (default)')}")
    if config.get('presets'):
        print(f"Mode:            PRESET (multi renders)")
        for i, (camera, frame) in enumerate(config['presets'], 1):
            print(f"  Preset {i}:      {camera} @ frame {frame}")
    else:
        print(f"Mode:            MULTI (all cameras)")
        if config.get('cameras'):
            print(f"Cameras:         {', '.join(config['cameras'])}")
        else:
            print(f"Cameras:         All")
    print(f"Output Dir:      {config['output_dir']}")
    print("=" * 60)
    print()
    
    # Find Blender executable
    blender_paths = [
        Path('C:/Program Files/Blender Foundation/Blender 4.5/blender.exe'),
        Path('/Applications/Blender.app/Contents/MacOS/Blender'),
        Path('/usr/bin/blender'),
        Path('/snap/bin/blender'),
    ]
    
    blender_exe = None
    for path in blender_paths:
        if path.exists():
            blender_exe = path
            break
    
    if not blender_exe:
        print("Error: Blender executable not found. Please install Blender.")
        sys.exit(1)
    
    # Get blend file
    blend_file = Path(config['blend_file'])
    if not blend_file.exists():
        print(f"Error: Blend file not found: {blend_file}")
        sys.exit(1)
    
    # Run Blender
    try:
        print(f"Starting Blender render...")
        print(f"Blend file: {blend_file}")
        print()
        
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'
        
        result = subprocess.run(
            [str(blender_exe), str(blend_file), '--background', '--python', str(temp_script)],
            env=env,
            cwd=os.getcwd()
        )
        
        if result.returncode == 0:
            print()
            print("=" * 60)
            print("✓ RENDER COMPLETE!")
            print("=" * 60)
            print(f"Output saved to: {config['output_dir']}/")
        else:
            print()
            print("=" * 60)
            print("✗ RENDER FAILED")
            print("=" * 60)
            sys.exit(1)
    
    finally:
        # Clean up temp script
        if temp_script.exists():
            temp_script.unlink()
        
        # Restore placeholders in original script
        restore_content = script_content.replace(config['pattern'], '__PATTERN_PLACEHOLDER__')
        restore_content = restore_content.replace(blender_engine, '__ENGINE_PLACEHOLDER__')
        restore_content = restore_content.replace(str(config['samples']), '__SAMPLES_PLACEHOLDER__')
        restore_content = restore_content.replace(str(config['resolution_scale']), '__SCALE_PLACEHOLDER__')
        restore_content = restore_content.replace(str(config.get('output_width', 480)), '__OUTPUT_WIDTH_PLACEHOLDER__')
        restore_content = restore_content.replace(str(config.get('output_height', 480)), '__OUTPUT_HEIGHT_PLACEHOLDER__')
        restore_content = restore_content.replace(presets_str, '__PRESETS_PLACEHOLDER__')
        restore_content = restore_content.replace(cameras_str, '__CAMERAS_PLACEHOLDER__')
        if color_replacement:  # Only restore if there was a replacement
            restore_content = restore_content.replace(color_replacement, '__THREADS_COLOR_PLACEHOLDER__')
        
        with open(render_script_path, 'w', encoding='utf-8') as f:
            f.write(restore_content)

if __name__ == '__main__':
    main()

