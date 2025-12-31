""" EDL_SDk 模块，详细说明请见 README.md

"""

import sys, os

sdk_root_path = os.path.dirname(os.path.abspath(__file__))
if sdk_root_path not in sys.path:
    sys.path.insert(0, sdk_root_path)

