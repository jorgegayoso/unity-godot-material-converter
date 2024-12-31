import os
import re
from pathlib import Path

class UnityGodotConverter:
    def __init__(self):
        self.property_mappings = {
            '_MainTex': 'albedo_texture',
            '_Color': 'albedo_color',
            '_Metallic': 'metallic',
            '_Glossiness': 'roughness',
            '_BumpMap': 'normal_texture',
            '_EmissionColor': 'emission',
            '_EmissionMap': 'emission_texture',
            '_OcclusionMap': 'ao_texture'
        }
        self.unity_texture_cache = {}
        self.godot_resource_cache = {}
        
    def find_meta_file_by_guid(self, project_root, guid):
        """Find a .meta file containing the specified GUID."""
        cache_key = f"{project_root}:{guid}"
        if cache_key in self.unity_texture_cache:
            return self.unity_texture_cache[cache_key]

        print(f"Searching for GUID: {guid}")
        
        for root, dirs, files in os.walk(project_root):
            for file in files:
                if file.endswith('.meta'):
                    meta_path = os.path.join(root, file)
                    try:
                        with open(meta_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if f'guid: {guid}' in content:
                                asset_path = meta_path[:-5]
                                if os.path.exists(asset_path):
                                    self.unity_texture_cache[cache_key] = asset_path
                                    return asset_path
                    except UnicodeDecodeError:
                        continue
        
        self.unity_texture_cache[cache_key] = None
        return None

    def find_godot_resource(self, godot_project_root, unity_path):
        """Find corresponding Godot resource for a Unity asset."""
        if not unity_path:
            return None

        cache_key = f"{godot_project_root}:{unity_path}"
        if cache_key in self.godot_resource_cache:
            return self.godot_resource_cache[cache_key]

        base_name = os.path.splitext(os.path.basename(unity_path))[0]
        extensions = ['.png'] if unity_path.lower().endswith('.psd') else [os.path.splitext(unity_path)[1], '.png']
        
        for ext in extensions:
            for root, dirs, files in os.walk(godot_project_root):
                for file in files:
                    if file.lower() == (base_name.lower() + ext.lower()):
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, godot_project_root)
                        godot_path = "res://" + rel_path.replace('\\', '/')
                        self.godot_resource_cache[cache_key] = godot_path
                        return godot_path
                        
        self.godot_resource_cache[cache_key] = None
        return None

    def analyze_unity_material(self, mat_path):
        """Analyze a Unity material file and find its actual texture files."""
        try:
            with open(mat_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(mat_path, 'r', encoding='latin-1') as f:
                content = f.read()

        name_match = re.search(r'm_Name: (.+)', content)
        material_name = name_match.group(1).strip() if name_match else "Unknown"

        textures = {}
        tex_pattern = r'_(\w+):\s*\n\s*m_Texture:\s*{fileID:\s*(\d+),\s*guid:\s*([a-f0-9]{32})'
        
        for match in re.finditer(tex_pattern, content):
            prop_name, file_id, guid = match.groups()
            if file_id != "0":
                textures[prop_name] = {
                    'fileID': file_id,
                    'guid': guid
                }

        float_pattern = r'm_Floats:\s*((?:\s*-\s*_\w+:\s*[\d.]+\s*)+)'
        float_matches = re.search(float_pattern, content)
        float_properties = {}
        if float_matches:
            float_text = float_matches.group(1)
            for float_match in re.finditer(r'-\s*(_\w+):\s*([\d.]+)', float_text):
                prop_name, value = float_match.groups()
                float_properties[prop_name] = float(value)

        color_pattern = r'm_Colors:\s*((?:\s*-\s*_\w+:\s*{[^}]+}\s*)+)'
        color_matches = re.search(color_pattern, content)
        color_properties = {}
        if color_matches:
            color_text = color_matches.group(1)
            for color_match in re.finditer(r'-\s*(_\w+):\s*{r:\s*([\d.]+),\s*g:\s*([\d.]+),\s*b:\s*([\d.]+),\s*a:\s*([\d.]+)}', color_text):
                prop_name, r, g, b, a = color_match.groups()
                color_properties[prop_name] = {
                    'r': float(r),
                    'g': float(g),
                    'b': float(b),
                    'a': float(a)
                }

        keywords_pattern = r'm_ShaderKeywords:\s*(.*)'
        keywords_match = re.search(keywords_pattern, content)
        shader_keywords = keywords_match.group(1).strip() if keywords_match else ""

        return {
            'name': material_name,
            'path': mat_path,
            'textures': textures,
            'floats': float_properties,
            'colors': color_properties,
            'shader_keywords': shader_keywords
        }

    def convert_color(self, unity_color):
        """Convert Unity color (RGBA) to Godot color format."""
        if isinstance(unity_color, dict):
            r = unity_color.get('r', 1.0)
            g = unity_color.get('g', 1.0)
            b = unity_color.get('b', 1.0)
            a = unity_color.get('a', 1.0)
            return f"Color({r}, {g}, {b}, {a})"
        return "Color(1, 1, 1, 1)"

    def generate_godot_material(self, unity_material, unity_project_root, godot_project_root, output_path):
        """Generate Godot .tres file from Unity material data."""
        tres_content = '[gd_resource type="StandardMaterial3D" format=3]\n\n'
        tres_content += '[resource]\n'
        
        keywords = unity_material['shader_keywords']
        if '_ALPHATEST_ON' in keywords:
            tres_content += 'transparency = 1\n'
            tres_content += f'alpha_scissor_threshold = {unity_material["floats"].get("_Cutoff", 0.5)}\n'
            tres_content += 'alpha_hash_scale = 1.0\n'
        elif '_ALPHABLEND_ON' in keywords or '_ALPHAPREMULTIPLY_ON' in keywords:
            tres_content += 'transparency = 1\n'
            tres_content += 'blend_mode = 1\n'

        for unity_prop, godot_prop in self.property_mappings.items():
            if unity_prop in unity_material['textures']:
                tex_info = unity_material['textures'][unity_prop]
                unity_path = self.find_meta_file_by_guid(unity_project_root, tex_info['guid'])
                if unity_path:
                    godot_path = self.find_godot_resource(godot_project_root, unity_path)
                    if godot_path:
                        print(f"  Found texture: {os.path.basename(unity_path)} -> {godot_path}")
                        tres_content += f'{godot_prop} = ExtResource("{godot_path}")\n'
                    else:
                        print(f"  Warning: Could not find Godot resource for {os.path.basename(unity_path)}")
            elif unity_prop in unity_material['colors']:
                color_value = unity_material['colors'][unity_prop]
                tres_content += f'{godot_prop} = {self.convert_color(color_value)}\n'
            elif unity_prop in unity_material['floats']:
                value = unity_material['floats'][unity_prop]
                if unity_prop == '_Glossiness':
                    value = 1.0 - value
                tres_content += f'{godot_prop} = {value}\n'

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(tres_content)

    def find_godot_fbx(self, unity_fbx_path, unity_root, godot_root, unity_assets_dir, godot_assets_dir):
        """Find corresponding FBX file in the Godot project using multiple search strategies."""
        fbx_name = os.path.basename(unity_fbx_path)
        
        # Strategy 1: Map directly between asset directories
        rel_path = os.path.relpath(unity_fbx_path, unity_assets_dir)
        godot_fbx_path = os.path.join(godot_assets_dir, rel_path)
        
        if os.path.exists(godot_fbx_path):
            print(f"Found FBX via direct mapping: {godot_fbx_path}")
            # Convert to res:// path relative to Godot project root
            godot_res_path = os.path.relpath(godot_fbx_path, godot_root)
            return "res://" + godot_res_path.replace('\\', '/')
            
        # Strategy 2: Try to find the FBX anywhere in the Godot assets directory
        print(f"Direct path not found, searching for {fbx_name} in {godot_assets_dir}...")
        for root, dirs, files in os.walk(godot_assets_dir):
            if fbx_name in files:
                found_path = os.path.join(root, fbx_name)
                rel_path = os.path.relpath(found_path, godot_root)
                print(f"Found FBX via search: {found_path}")
                return "res://" + rel_path.replace('\\', '/')
                
        print(f"Could not find {fbx_name} in Godot project")
        return None

    def generate_godot_scene(self, fbx_path, material_mappings, unity_root, godot_root, unity_assets_dir, godot_assets_dir, output_dir):
        """Generate a Godot scene file (.tscn) that imports the FBX and assigns materials."""
        fbx_name = os.path.splitext(os.path.basename(fbx_path))[0]
        
        # Create Scenes directory inside the Godot assets directory
        scenes_dir = os.path.join(godot_assets_dir, 'Scenes')
        os.makedirs(scenes_dir, exist_ok=True)
        
        # Get the path relative to the Unity assets directory, but only keep the part after Meshes
        full_rel_path = os.path.relpath(fbx_path, unity_assets_dir)
        path_parts = full_rel_path.split(os.sep)
        
        # Find the 'Meshes' part and keep everything after it
        try:
            meshes_index = path_parts.index('Meshes')
            relevant_path = os.path.join(*path_parts[meshes_index:])
        except ValueError:
            # If 'Meshes' is not found, use the full path
            relevant_path = full_rel_path
            
        scene_subdir = os.path.join(scenes_dir, os.path.dirname(relevant_path))
        os.makedirs(scene_subdir, exist_ok=True)
        output_path = os.path.join(scene_subdir, f"{fbx_name}.tscn")
        
        # Get the Godot resource path for the FBX
        godot_fbx_path = self.find_godot_fbx(fbx_path, unity_root, godot_root, unity_assets_dir, godot_assets_dir)
        if not godot_fbx_path:
            print(f"Warning: Could not find corresponding FBX in Godot project for {fbx_path}")
            return None
            
        # Generate the scene file content
        tscn_content = '[gd_scene load_steps=2 format=3]\n\n'
        tscn_content += f'[ext_resource type="PackedScene" path="{godot_fbx_path}" id="1"]\n\n'
        tscn_content += f'[node name="{fbx_name}" instance=ExtResource("1")]\n\n'
        
        # Apply material overrides
        for mesh_name, material_path in material_mappings.items():
            tscn_content += f'[node name="{mesh_name}" parent="." index="0"]\n'
            tscn_content += f'material_override = ExtResource("{material_path}")\n\n'
        
        # Write the scene file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(tscn_content)
        
        return output_path
        
        # Generate the scene file content
        tscn_content = '[gd_scene load_steps=2 format=3]\n\n'
        
        # Add the external resource references
        tscn_content += '[ext_resource type="PackedScene" path="%s" id="1"]\n\n' % fbx_res_path
        
        # Create the scene tree
        tscn_content += '[node name="%s" instance=ExtResource("1")]\n\n' % fbx_name
        
        # Apply material overrides
        for mesh_name, material_path in material_mappings.items():
            tscn_content += '[node name="%s" parent="." index="0"]\n' % mesh_name
            tscn_content += 'material_override = ExtResource("%s")\n\n' % material_path
        
        # Write the scene file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(tscn_content)
        
        return output_path

    def convert_directory(self, input_dir, output_dir, unity_project_root, godot_project_root):
        """Convert all materials and create scene files with proper material assignments."""
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        
        # Find all .mat and .fbx files
        mat_files = list(input_path.glob('**/*.mat'))
        fbx_files = list(input_path.glob('**/*.fbx'))
        
        print(f"\nFound {len(mat_files)} material files and {len(fbx_files)} FBX files.")
        print("\nConverting materials...")
        
        # Convert all materials first
        material_paths = {}  # Map of material names to their Godot paths
        for mat_file in mat_files:
            relative_path = mat_file.relative_to(input_path)
            output_file = output_path / relative_path.with_suffix('.tres')
            
            try:
                material_info = self.analyze_unity_material(mat_file)
                if material_info:
                    self.generate_godot_material(
                        material_info,
                        unity_project_root,
                        godot_project_root,
                        output_file
                    )
                    # Store the Godot resource path for this material
                    godot_mat_path = f"res://{output_file.relative_to(Path(godot_project_root))}".replace('\\', '/')
                    material_paths[material_info['name']] = godot_mat_path
                    print(f"Converted material: {mat_file.name} -> {output_file.name}")
            except Exception as e:
                print(f"Error converting {mat_file}: {e}")

        print("\nCreating scene files with material assignments...")
        
        # Process each FBX file
        for fbx_file in fbx_files:
            print(f"\nProcessing {fbx_file.name}")
            try:
                # Create a scene file for this FBX
                material_mappings = {}
                for mat_name, mat_path in material_paths.items():
                    if mat_name.lower() in fbx_file.stem.lower():
                        material_mappings[fbx_file.stem] = mat_path
                
                scene_path = self.generate_godot_scene(
                    str(fbx_file),
                    material_mappings,
                    unity_project_root,
                    godot_project_root,
                    input_dir,  # Unity assets directory
                    output_dir,  # Godot assets directory
                    output_dir
                )
                if scene_path:
                    print(f"Created scene file: {scene_path}")
                
            except Exception as e:
                print(f"Error processing {fbx_file}: {e}")

        print("\nConversion complete!")

def main():
    converter = UnityGodotConverter()
    
    unity_project_root = input("Enter Unity project root directory: ").strip('"')
    godot_project_root = input("Enter Godot project root directory: ").strip('"')
    input_dir = input("Enter directory containing Unity assets: ").strip('"')
    output_dir = input("Enter directory containing Godot assets: ").strip('"')
    
    if not all(os.path.exists(p) for p in [unity_project_root, godot_project_root, input_dir]):
        print("One or more paths do not exist!")
        return
        
    os.makedirs(output_dir, exist_ok=True)
    
    converter.convert_directory(input_dir, output_dir, unity_project_root, godot_project_root)

if __name__ == "__main__":
    main()
