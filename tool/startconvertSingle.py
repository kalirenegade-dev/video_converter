import shutil
import subprocess
import os

shutil.copyfile(r"C:\tool\convert.py", "convert.py")
shutil.copyfile(r"C:\tool\HandBrakeCLI.exe", "HandBrakeCLI.exe")

path = 'convert.py -r -a -l "C:\\tool\convert.log"'
subprocess.call(path, shell=True)

os.remove("convert.py")
os.remove("HandBrakeCLI.exe")

