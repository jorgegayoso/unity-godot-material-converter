# Unity to Godot Material Converter

This script converts Unity materials to Godot materials and creates scene files that automatically assign these materials to their corresponding models.

## Prerequisites

- Python 3.6 or higher
- A Unity project with materials and models
- A Godot project where you want to use these assets

## Setup

1. First, copy your Unity asset folder structure to your Godot project. For example, if you have:
   ```
   Unity Project/Assets/MyAssets/Models/
                                    /Materials/
                                    /Textures/
   ```
   Copy this entire folder structure (excluding the Materials folder) to your Godot project, maintaining the same hierarchy.
   **Make sure to open the project so the files get imported before proceeding**

2. Install the required Python dependencies:
   ```bash
   pip install pathlib
   ```

## Usage

1. Run the script:
   ```bash
   python unity_godot_material_converter.py
   ```

2. You will be prompted to enter four paths:

   - Unity project root directory
   - Godot project root directory
   - Directory containing Unity assets
   - Directory containing Godot assets

### Example

Let's say you have the following structure:

Unity Project:
```
D:/Programming/Unity Projects/MyGame/
└── Assets/
    └── Foo/
        └── Low Poly/
            └── Vegetation/
                └── Vegetation Assets/
                    ├── Materials/
                    ├── Meshes/
                    └── Textures/
```

Godot Project:
```
D:/Programming/Godot Projects/MyGame/
└── Assets/
    └── Objects/
        └── Vegetation Assets/
            ├── Meshes/
            └── Textures/
```

You would enter:
```
Unity project root: D:/Programming/Unity Projects/MyGame
Godot project root: D:/Programming/Godot Projects/MyGame
Unity assets directory: D:/Programming/Unity Projects/MyGame/Assets/Foo/Low Poly/Vegetation/Vegetation Assets
Godot assets directory: D:/Programming/Godot Projects/MyGame/Assets/Objects/Vegetation Assets
```

## Output

The script will:
1. Convert all materials from the Unity project to Godot's .tres format
2. Create a Scenes folder in your Godot assets directory
3. Generate .tscn scene files that automatically assign the converted materials to their models
4. Maintain the folder structure of your meshes in the Scenes folder

Example output structure:
```
Vegetation Assets/
├── Materials/        # Converted .tres materials
├── Meshes/          # Your original meshes
├── Scenes/          # Generated scene files
│   └── Meshes/      # Matching folder structure
│       └── Plants/
└── Textures/        # Your original textures
```

## Notes

- The script assumes that the assets in your Godot project maintain the same folder structure as in Unity
- Materials will be converted to Godot's StandardMaterial3D format
- Scene files (.tscn) will be created with proper material assignments
- Original FBX files must be imported into Godot before using the generated scenes