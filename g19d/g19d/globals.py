import os
import sys

name = "g19d"
version = "0.0.7"
 
data_dir = os.path.abspath(os.path.dirname(__file__))
if not os.path.exists(os.path.join(data_dir, "g19daemon")):
    data_dir = "/usr/share/g19d"
