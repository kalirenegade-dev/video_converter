# video_converter
uses HandBrakeCLI.exe with the "General/Very Fast 720p30" profile to convert videos and keeps only the videos that are smaller in size


Move convert.py and HandBrakeCLI.exe into C:\tool\ on each computer


open Create Database.py and select your remote media path then run to generate a database

#localPath

path = 'W:\TV Shows'

folder_path = f"\\\\?\\{path}"

#networkPath

path = '\\ServerName\Media\TV Shows'

folder_path = f"\\\\?\\UNC{path}"

after that run Server.py

open Client.py and set the local ip of your server

server = "192.168.1.233"

on any computers that can access your media share weather on the network or network maped drive run Client.py

the client will query the server for a video to convert and convert it one at a time per client instence then reach out to the server when compleated to request a new video


you can run more then one Client.py per computer if your pc is strong enough

below is depreciated.

python 3 convert.py

arguments are 

-f    --force        will process videos previously processed

-r    --recursive    will process videos recursivaly inside folders

-p    --path         the path of the folder containing the videos

-a    --append       will append to the log instead of creating a new one

-g    --gpu          will use Gpu by enabling the nvenc_h264 flag

-l    --logfile      location of log file

-l    --cleanup      removes any failed converted files


startconvertSingle.py

Drag into the folder you want to convert all files in and run

