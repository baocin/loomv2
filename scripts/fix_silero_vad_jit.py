#!/usr/bin/env python3
"""
Fix Silero VAD TorchScript corruption issue.

The issue: TorchScript in the model became invalid due to PyTorch changes.
The fix: Replace invalid torch.__not__ operation with torch.eq.

Based on solution from: https://github.com/snakers4/silero-vad/discussions/531
"""

import os
import tempfile
import zipfile
import shutil


def fix_silero_vad_jit(model_path: str) -> bool:
    """
    Fix the TorchScript corruption in Silero VAD JIT model.

    Args:
        model_path: Path to the silero_vad.jit file

    Returns:
        True if fix was applied successfully, False otherwise
    """
    if not os.path.exists(model_path):
        print(f"Model file not found: {model_path}")
        return False

    print(f"Fixing Silero VAD JIT model: {model_path}")

    # Create backup
    backup_path = f"{model_path}.backup"
    shutil.copy2(model_path, backup_path)
    print(f"Created backup: {backup_path}")

    # Create temporary directory for extraction
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Extracting JIT model to: {temp_dir}")

        # Extract the JIT file (it's a ZIP archive)
        try:
            with zipfile.ZipFile(model_path, "r") as zip_ref:
                zip_ref.extractall(temp_dir)
        except zipfile.BadZipFile:
            print("Error: JIT file is not a valid ZIP archive")
            return False

        # Find the vad_annotator.py file
        annotator_path = None
        for root, dirs, files in os.walk(temp_dir):
            if "vad_annotator.py" in files:
                annotator_path = os.path.join(root, "vad_annotator.py")
                break

        if not annotator_path:
            print("Error: vad_annotator.py not found in JIT model")
            return False

        print(f"Found vad_annotator.py: {annotator_path}")

        # Read the file and apply the fix
        with open(annotator_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Apply the fix: replace the invalid TorchScript operation
        original_code = "_9 = torch.__not__(bool(torch.len(_context)))"
        fixed_code = "_9 = torch.eq(torch.len(_context), 0)"

        if original_code in content:
            print("Applying TorchScript fix...")
            content = content.replace(original_code, fixed_code)

            # Write the fixed content back
            with open(annotator_path, "w", encoding="utf-8") as f:
                f.write(content)

            print("Fix applied successfully")
        else:
            print(
                "Warning: Original code pattern not found - model may already be fixed"
            )

        # Rebuild the JIT model as a ZIP archive
        print(f"Rebuilding JIT model: {model_path}")
        with zipfile.ZipFile(model_path, "w", zipfile.ZIP_DEFLATED) as zip_ref:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arc_path = os.path.relpath(file_path, temp_dir)
                    zip_ref.write(file_path, arc_path)

        print("JIT model rebuilt successfully")
        return True


def main():
    """Main function to fix Silero VAD JIT models."""
    # Common locations where Silero VAD models might be cached
    cache_locations = [
        "/home/appuser/.cache/torch/hub/snakers4_silero-vad_master",
        "/root/.cache/torch/hub/snakers4_silero-vad_master",
        "~/.cache/torch/hub/snakers4_silero-vad_master",
    ]

    fixed_count = 0

    for location in cache_locations:
        expanded_location = os.path.expanduser(location)
        if os.path.exists(expanded_location):
            print(f"Checking location: {expanded_location}")

            # Look for JIT files
            for root, dirs, files in os.walk(expanded_location):
                for file in files:
                    if file.endswith(".jit") and "vad" in file.lower():
                        jit_path = os.path.join(root, file)
                        print(f"Found JIT model: {jit_path}")

                        if fix_silero_vad_jit(jit_path):
                            fixed_count += 1
                        else:
                            print(f"Failed to fix: {jit_path}")

    if fixed_count > 0:
        print(f"\nSuccessfully fixed {fixed_count} Silero VAD JIT model(s)")
    else:
        print("\nNo Silero VAD JIT models found or fixed")

    return fixed_count > 0


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
