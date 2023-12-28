import asyncio
import websockets
import json
import time
import subprocess
from tqdm import tqdm
import os
import argparse
import shutil
import socket
import sqlite3
import winsound

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    
    
Isbeep = False

# Connect to SQLite database (or create if it doesn't exist)
conn = sqlite3.connect('videodb.db')

# Create a cursor object to execute SQL queries
cursor = conn.cursor()
max_processing_state_count = 0
counter = 0
def get_max_processing_state_count():
    cursor.execute('''
        SELECT COUNT(*) FROM videos
        WHERE processing_state = 0
    ''')
    return cursor.fetchone()[0]

def MarkNotFound(video_id):
        cursor.execute('''
            UPDATE videos
            SET processing_state = 4
            WHERE id = ?
        ''', (video_id,))
        conn.commit()

def MarkInvalid(video_id):
        cursor.execute('''
            UPDATE videos
            SET processing_state = 3
            WHERE id = ?
        ''', (video_id,))
        conn.commit()

def ResetState():
        cursor.execute('''
            UPDATE videos
            SET processing_state = ?
            WHERE 1=1
        ''', (0,))
        conn.commit()
        
def MarkConverted(video_id):
        cursor.execute('''
            UPDATE videos
            SET processing_state = 2
            WHERE id = ?
        ''', (video_id,))
        conn.commit()

def MarkProcessing(video_id):
        cursor.execute('''
            UPDATE videos
            SET processing_state = 1
            WHERE id = ?
        ''', (video_id,))
        conn.commit()

def getVideo():
    # Select one video with processing_state=0
    cursor.execute('''
        SELECT * FROM videos
        WHERE processing_state = 0
        LIMIT 1
    ''')

    # Fetch the result
    video = cursor.fetchone()

    # Check if a video was found
    if video:
        video_id, videopath, processing_state = video
        #print(f"Video ID: {video_id}, Video Path: {videopath}, Processing State: {processing_state}")
        # Update processing state to 1
        MarkProcessing(video_id)

        #print(f"Processing state updated to 1 for Video ID: {video_id}")
        return(videopath, video_id)

    else:
        print("No video with processing_state=0 found")
        return(None, None)

def separate_path_filename_extension(file_path):
    # Split the file path into directory, base name, and extension
    directory, file_name_with_extension = os.path.split(file_path)
    # Split the base name and extension
    file_name, file_extension = os.path.splitext(file_name_with_extension)
    return directory, file_name, file_extension
    
def handbrake_command_gen(file_path):
    handbrake_command = None
    directory, file_name, file_extension = separate_path_filename_extension(file_path)

    handbrake_command = [
        'HandBrakeCLI.exe', '--json',
        '--scan',
        '-i', file_path,
    ]

    return handbrake_command

def ConvertFile(input_file):
    global counter
    global Isbeep
    try:
        handbrake_command = handbrake_command_gen(input_file) 
        p = subprocess.Popen(handbrake_command, stdout=subprocess.PIPE, text=True, stderr=subprocess.STDOUT, encoding='utf-8', errors='replace')
        with tqdm(total=100, dynamic_ncols=True, desc="Checking file... ") as prbar:
            while (line := p.stdout.readline()) != "":

                line = line.rstrip()
                #print(line)

        Return_code = p.wait()
        if(Return_code == 2):
            ErrorMsg(f"Invalid Video: '{input_file}'")
            if (Isbeep):
                beep()
        elif (Return_code == 0):
            OkMsg(f"Valid Video: '{input_file}'")
        else:
            print(f"End of output.  Return code: {Return_code}")   
        counter += 1            
    except subprocess.CalledProcessError as e:
        print(f"Conversion failed with error code {e.returncode}")
    
def beep():
    frequency = 2500  # Set Frequency To 2500 Hertz
    duration = 1000  # Set Duration To 1000 ms == 1 second
    winsound.Beep(frequency, duration)    
def copyFile():
    source_path = "C:\\tool\\HandBrakeCLI.exe"
    destination_path = "HandBrakeCLI.exe" 
    try:
        # Attempt to copy the file
        shutil.copyfile(source_path, destination_path)
    except FileNotFoundError:
        pass
        #print(f"Source file '{source_path}' not found.")
    except PermissionError:
        pass
        #print(f"Permission error: Unable to copy file to '{destination_path}'.")
    except Exception as e:
        pass
        #print(f"CopyFile: An unexpected error occurred: {e}")

def deleteFile():
    source_path = 'HandBrakeCLI.exe'
    try:
        # Attempt to remove the file
        os.remove(source_path)
    except FileNotFoundError:
        pass
        #print(f"File '{source_path}' not found.")
    except PermissionError:
        pass
        #print(f"Permission error: Unable to delete file '{source_path}'.")
    except Exception as e:
        pass
        #print(f"deleteFile: An unexpected error occurred: {e}")

def ErrorMsg(message):
    error_message = f"{bcolors.FAIL}{message}{bcolors.ENDC}"
    # Append the error message to a file
    with open('error_log.txt', 'a') as log_file:
        log_file.write(message + '\n')
    print(error_message)
    
def OkMsg(message):
    print(f"{bcolors.OKGREEN}{message}{bcolors.ENDC}")

def Start(counter):
    while True:
        VideoPath, video_id = getVideo()
        if VideoPath is not None:
            max_processing_state_count = get_max_processing_state_count()
            os.system("title " + f"({counter}/{max_processing_state_count})") 
            ConvertFile(VideoPath)
            counter += 1
        else:
            break
    return counter
    

        
copyFile()

ResetState()

counter = Start(counter)
deleteFile()

conn.commit()
conn.close()
    
                        