import os
import numpy as np
# Monkey patch for tf2onnx compatibility with NumPy 2.0+ (Python 3.13)
# tf2onnx relies on np.cast which was removed in NumPy 2.0.
try:
    np.cast
except AttributeError:
    np.cast = lambda x, y: np.asarray(x, dtype=y)

import tensorflow as tf
import tf2onnx

def convert_to_onnx():
    input_model_path = "models/trajectory_model.keras"
    output_model_path = "models/trajectory_model.onnx"

    if not os.path.exists(input_model_path):
        print(f"Error: Input model '{input_model_path}' not found.")
        print("Please run ML1.py first to train and save the model.")
        return

    print(f"Loading model from '{input_model_path}'...")
    try:
        model = tf.keras.models.load_model(input_model_path)
        
        # Hardcoded input shape based on ML1.py (N_STEPS=30, N_FEATURES=38)
        # The model expects a batch dimension (None)
        input_signature = [tf.TensorSpec((None, 30, 38), tf.float32, name="input")]
        
        # Convert
        # Keras 3 compatibility fix: Save as TF SavedModel first, then convert.
        # Direct conversion from Keras 3 objects often fails with 'output_names' error.
        temp_saved_model = "temp_tf_saved_model"
        if os.path.exists(temp_saved_model):
            import shutil
            shutil.rmtree(temp_saved_model)
            
        print(f"Saving temporary TF model to '{temp_saved_model}'...")
        model.export(temp_saved_model) # Keras 3 export
        
        print(f"Converting to ONNX (output: '{output_model_path}')...")
        # Use tf2onnx.convert.main() directly to run in the same process
        # This ensures the np.cast monkey patch is applied.
        import sys
        from tf2onnx.convert import main as tf2onnx_main
        
        # Mock sys.argv
        original_argv = sys.argv
        sys.argv = [
            "tf2onnx.convert",
            "--saved-model", temp_saved_model,
            "--output", output_model_path,
            "--opset", "13"
        ]
        
        try:
            tf2onnx_main()
            print(f"Success! Model saved to '{output_model_path}'")
        except SystemExit as e:
            if e.code == 0:
                print(f"Success! Model saved to '{output_model_path}'")
            else:
                print(f"tf2onnx exited with code {e.code}")
        except Exception as e:
            print(f"Error converting to ONNX: {e}")
            import traceback
            traceback.print_exc()
        finally:
            sys.argv = original_argv
            
        # Cleanup
        if os.path.exists(temp_saved_model):
            import shutil
            shutil.rmtree(temp_saved_model)
        
    except Exception as e:
        print(f"Error during conversion: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    convert_to_onnx()
