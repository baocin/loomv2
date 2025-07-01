#!/usr/bin/env python3
"""Test script to verify Kyutai model loading."""

import torch
from moshi.models import loaders

def test_model_loading():
    """Test loading the Kyutai Mimi model."""
    print("Testing Kyutai model loading...")
    
    try:
        # Check CUDA availability
        print(f"CUDA available: {torch.cuda.is_available()}")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {device}")
        
        # Load checkpoint info
        print("\nLoading checkpoint info from HuggingFace...")
        checkpoint_info = loaders.CheckpointInfo.from_hf_repo("kyutai/stt-1b-en_fr")
        print("✓ Checkpoint info loaded successfully")
        
        # Load Mimi model
        print("\nLoading Mimi encoder...")
        mimi = checkpoint_info.get_mimi(device=device)
        print(f"✓ Mimi model loaded successfully")
        print(f"  Sample rate: {mimi.sample_rate} Hz")
        
        # Load text tokenizer
        print("\nLoading text tokenizer...")
        text_tokenizer = checkpoint_info.get_text_tokenizer()
        print(f"✓ Text tokenizer loaded successfully")
        print(f"  Vocab size: {text_tokenizer.get_piece_size()}")
        
        # Load language model
        print("\nLoading language model (this may take a while)...")
        lm = checkpoint_info.get_moshi(device=device)
        print("✓ Language model loaded successfully")
        
        print("\n✅ All models loaded successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error loading models: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_model_loading()
    exit(0 if success else 1)