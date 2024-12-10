


import subprocess

# Path to your .ui file
ui_file_path = r"photosequence_gen_dialog_base.ui"

# Path to where you want to save the converted .py file
output_file_path = r"photosequence_gen_dialog_base.py"

# Run the pyuic5 command via subprocess
subprocess.run(['pyuic5', ui_file_path, '-o', output_file_path])

print("Conversion complete!")