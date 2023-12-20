# video_converter
uses HandBrakeCLI.exe with the "General/Very Fast 720p30" profile to convert videos and keeps only the videos that are smaller in size


python 3 convert.py

arguments are 

-f    --force        will process videos previously processed

-r    --recursive    will process videos recursivaly inside folders

-p    --path         the path of the folder containing the videos

-a    --append       will append to the log instead of creating a new one

-g    --gpu          will use Gpu by enabling the nvenc_h264 flag

-l    --logfile      location of log file