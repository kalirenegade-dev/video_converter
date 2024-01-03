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
import atexit
import signal  # Import the signal module


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

Current_FileName = None
Current_video_id = None



TotalSpaceSaving = 0
gpu = False
server = "192.168.1.174"

#ServerIdentity = 'dell_laptop'
ServerIdentity = socket.gethostname()

uri = f"ws://{server}:8765"  # Replace with the address of your WebSocket server

async def SendData(data):
    global uri
    while True:
        try:
            async with websockets.connect(uri) as websocket:          
                message = json.dumps(data, indent=2)
                await websocket.send(message)              
                break
        except websockets.exceptions.ConnectionClosedError as e:
            print(f"Connection closed unexpectedly: {e}")
        except websockets.exceptions.WebSocketException as e:
            print(f"WebSocket exception: {e}")
        except ConnectionRefusedError as e:
            print(f"The remote computer refused the network connection")
            time.sleep(5)
        except Exception as e:
            print(f"SendData: An unexpected error occurred: {e}")
        #finally:
            #await websocket.close()

async def processVideo(videopath, video_id):
    try:
        print(f"{bcolors.OKGREEN}Processing video: '{videopath}', video_id: '{video_id}'{bcolors.ENDC}")
        FileName, SpaceSaved, error = await StartProcess(videopath)
        
        if error == 'Invalid':
            data = {
                "FileName": FileName,
                "error": 'InvalidVideo',
                "video_id": video_id,
            }
            await SendData(data)
            print(f"Sending completion message to '{uri}'\n")

        if error is None:
            data = {
                "FileName": FileName,
                "SpaceSaved": SpaceSaved,
                "video_id": video_id,
            }
            await SendData(data)
            print(f"Sending completion message to '{uri}'\n")
        
        await connect_to_server()

    except Exception as e:
        print(f"processVideo: An unexpected error occurred while processing video: {e}")


async def connect_to_server():
    global Current_FileName
    global Current_video_id
    
    Current_FileName = None
    Current_video_id = None
    while True:
        try:
            async with websockets.connect(uri) as websocket:
                data = {
                    "command": "RequestVideo",
                    "ServerIdentity": ServerIdentity,
                }

                # Send a message to the server
                message = json.dumps(data, indent=2)
                print(f"{bcolors.OKBLUE}Requesting New Video from '{uri}',  ServerIdentity: {ServerIdentity}{bcolors.ENDC}")
                await websocket.send(message)
                # print(f"Sent message: {message}")

                response = await websocket.recv()
                await websocket.close()

                try:
                    # Parse the JSON message
                    data = json.loads(response)
                    if "VideoPath" in data and "video_id" in data and "ServerIdentity" in data and data[
                        "ServerIdentity"] == ServerIdentity:
                        if data["VideoPath"] is None:
                            print("No More Videos to process")
                            break
                        #print(f"Received message: {response}")
                        VideoPath = data["VideoPath"]
                        
                        video_id = data["video_id"]
                        print(f"{bcolors.OKBLUE}New video Received, VideoPath: '{VideoPath}', id: '{video_id}'{bcolors.ENDC}")  
                        if os.path.isfile(VideoPath):
                            
                            Current_FileName = VideoPath
                            Current_video_id = video_id
    
                            await processVideo(VideoPath, video_id)
                        else:
                            print(f"{bcolors.FAIL}File Not Found: '{VideoPath}'{bcolors.ENDC}")
                            data = {
                                "FileName": VideoPath,
                                "error": 'NotFound',
                                "video_id": video_id,
                            }
                            await SendData(data)
                            print(f"Sending completion message to '{uri}'\n")
                            time.sleep(1)
                            await connect_to_server()

                        break  # Exit the loop when a valid response is received
                    else:
                        print("Invalid response")
                except json.JSONDecodeError:
                    print("Invalid JSON format")
        except websockets.exceptions.ConnectionClosedError as e:
            print(f"Connection closed unexpectedly: {e}")
        except websockets.exceptions.WebSocketException as e:
            print(f"WebSocket exception: {e}")
        except ConnectionRefusedError as e:
            print(f"The remote computer refused the network connection")
            time.sleep(5)
        except Exception as e:
            print(f"connect_to_server: An unexpected error occurred: {e}")    
            

def parse_arguments():
    global server
    global gpu

    parser = argparse.ArgumentParser(description='Video conversion script with optional force flag.')
    parser.add_argument('-s', '--server', type=str, help='Specify the websocket server')
    parser.add_argument('-g', '--gpu', action='store_true', help='Uses Gpu by enabling the nvenc_h264 flag')
    args = parser.parse_args()
    
    # Update the force variable based on the command-line argument
    server = args.server
    gpu = args.gpu
    
def get_file_size(file_path):
    try:
        # Get the size of the file in bytes
        size_bytes = os.path.getsize(file_path)
        return size_bytes
    except FileNotFoundError:
        return None

def format_size_difference(difference):
    tb = abs(difference) / (1024**4)
    gb = abs(difference) / (1024**3)
    mb = abs(difference) / (1024**2)
    kb = abs(difference) / 1024
    if tb >= 1:
        return f"({tb:.2f} TB)"
    elif gb >= 1:
        return f"({gb:.2f} GB)"
    elif mb >= 1:
        return f"({mb:.2f} MB)"
    else:
        return f"({kb:.2f} KB)"

def separate_path_filename_extension(file_path):
    # Split the file path into directory, base name, and extension
    directory, file_name_with_extension = os.path.split(file_path)
    # Split the base name and extension
    file_name, file_extension = os.path.splitext(file_name_with_extension)
    return directory, file_name, file_extension

def is_output_smaller(file_path):
    directory, file_name, file_extension = separate_path_filename_extension(file_path)
    converted_file = os.path.join(directory, file_name + '-converted' + ".mp4")
    file_size = get_file_size(file_path)
    file_size_converted = get_file_size(converted_file)
    difference_bytes = file_size - file_size_converted
    #print(f"Difference in size: {format_size_difference(difference_bytes)}")
    return difference_bytes > 0, (f"{format_size_difference(difference_bytes)}"),difference_bytes

def handbrake_command_gen(file_path):
    global gpu
    directory, file_name, file_extension = separate_path_filename_extension(file_path)
    output_file_path = os.path.join(directory, file_name + '-converted' + ".mp4")

    if(gpu):
        handbrake_command = [
            'HandBrakeCLI.exe',
            '-e', 'nvenc_h264',
            '-Z', 'General/Very Fast 720p30',
            '-i', file_path,
            '-o', output_file_path,
        ]
        return handbrake_command
    else:
        handbrake_command = [
            'HandBrakeCLI.exe', '--json',
            '-Z', 'General/Very Fast 720p30',
            '-i', file_path,
            '-o', output_file_path,
        ]
        return handbrake_command
    


async def ConvertFile(input_file):
    FileSize_bytes = 0
    New_input_file = None
    try:
        handbrake_command = handbrake_command_gen(input_file) 
        #print(handbrake_command)
        #subprocess.run(handbrake_command, check=True) # old method just console passthough
        

        p = subprocess.Popen(handbrake_command, stdout=subprocess.PIPE, text=True, stderr=subprocess.STDOUT, encoding='utf-8', errors='replace')
        with tqdm(total=0, dynamic_ncols=True, desc="Compressing file with profile 'General/Very Fast 720p30' ... ") as prbar:
            while (line := p.stdout.readline()) != "":
                line = line.rstrip()
                #print(line)
                            
                if '"ETASeconds"' in line:
                    try:
                        ETA_seconds = int(line.split(":")[1].lstrip(".").replace(",", "").strip())
                        eta_hours, remainder = divmod(ETA_seconds, 3600)
                        eta_minutes, eta_seconds = divmod(remainder, 60)
                        eta_formatted = f"{eta_hours:02d}:{eta_minutes:02d}:{eta_seconds:02d}"
                        prbar.set_postfix(eta=eta_formatted)
                    except ValueError as e:
                        # Handle the exception (e.g., print an error message or set a default value)
                        print(f"Error converting to integer: {e}, line: {line}")
                        # Set a default value for eta_formatted or handle it in a way that makes sense for your application
                        eta_formatted = "00:00:00"
                        prbar.set_postfix(eta=eta_formatted)
        Return_code = p.wait()
        if(Return_code == 2):
            print(f"{bcolors.FAIL}Invalid Video: '{input_file}'{bcolors.ENDC}")
            return input_file, FileSize_bytes, 'Invalid'
        elif (Return_code == 0):
            print(f"{bcolors.OKBLUE}converting video successful..{bcolors.ENDC}")
            directory, file_name, file_extension = separate_path_filename_extension(input_file)
            output_file_path_converted = os.path.join(directory, file_name + '-converted' + ".mp4")
            output_file_path_Checked= os.path.join(directory, file_name + '-checked' + file_extension)
            #print("Conversion successful")
            IsSmaller,SizeDiffrence,inbytes = is_output_smaller(input_file)
            if IsSmaller:
                #print("The converted file would be smaller")
                #print("Delete old video / rename new vidio")
                try:
                    New_input_file = output_file_path_converted
                    os.remove(input_file)
                    print(f"{bcolors.WARNING}The file '{file_name}{file_extension}' has been deleted successfully.{bcolors.ENDC}")
                except FileNotFoundError:
                    print(f"The file '{file_name}{file_extension}' does not exist.")
                except Exception as e:
                    print(f"An error occurred: {e}")
                print(f"{bcolors.OKCYAN}FileName: '{file_name}-converted.mp4' is smaller - Space Saved: {SizeDiffrence}{bcolors.ENDC}")
                FileSize_bytes = inbytes
            else:
                #print("The converted file would be SizeDiffrence")
                #print("Delete converted video")
                try:
                    New_input_file = output_file_path_Checked
                    os.remove(output_file_path_converted)
                    print(f"{bcolors.WARNING}The file '{output_file_path_converted}' has been deleted successfully.{bcolors.ENDC}")
                except FileNotFoundError:
                    print(f"The file '{output_file_path_converted}' does not exist.")
                except Exception as e:
                    print(f"An error occurred: {e}")
                try:
                    os.rename(input_file, output_file_path_Checked)
                    print(f"{bcolors.OKCYAN}The file '{input_file}' has been renamed to '{input_file}' successfully.{bcolors.ENDC}")
                except FileNotFoundError:
                    print(f"The file '{input_file}' does not exist.")
                except Exception as e:
                    print(f"An error occurred: {e}")
                print(f"FileName: '{file_name}{file_extension}' is smaller by {SizeDiffrence}")
        else:
            print(f"End of output.  Return code: {Return_code}")
          
           
    except subprocess.CalledProcessError as e:
        print(f"Conversion failed with error code {e.returncode}")
    return New_input_file, FileSize_bytes, None
    
def has_converted_in_filename(file_path):
    _, file_name = os.path.split(file_path)
    return "-converted" in file_name

def has_checked_in_filename(file_path):
    _, file_name = os.path.split(file_path)
    return "-checked" in file_name

async def StartProcess(video_file):
    directory, file_name, file_extension = separate_path_filename_extension(video_file)
    output_file_path_converted = os.path.join(directory, file_name + '-converted' + ".mp4")
    if os.path.exists(video_file) and os.path.exists(output_file_path_converted):
        try:
            os.remove(output_file_path_converted)
            print(f"{bcolors.WARNING}The file '{file_name}-converted.mp4' has been deleted successfully.{bcolors.ENDC}")
        except FileNotFoundError:
            print(f"The file '{file_name}-converted.mp4' does not exist.")
        except Exception as e:
            print(f"An error occurred: {e}")
    if(has_converted_in_filename(video_file) or has_checked_in_filename(video_file)):
        pass
    else:
      
        FileName, SpaceSaved, error = await ConvertFile(video_file)
        return FileName, SpaceSaved, error
    
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

def cleanup_on_exit():
    global Current_FileName
    global Current_video_id
    
    if Current_FileName and Current_video_id:
        data = {
            "FileName": Current_FileName,
            "error": 'incomplete',
            "video_id": Current_video_id,
        }
        asyncio.run(SendData(data))
        print(f"Sending completion message to '{uri}'\n")
    deleteFile()
    
# Register the cleanup function with atexit
atexit.register(cleanup_on_exit)
# Register a signal handler for SIGTERM
def sigterm_handler(signum, frame):
    print("Received SIGTERM. Closing WebSocket connection.")
    cleanup_on_exit()

signal.signal(signal.SIGTERM, sigterm_handler)
#signal.signal(signal.SIGINT, sigterm_handler)
parse_arguments()

    
copyFile()
try:
    asyncio.run(connect_to_server())
except KeyboardInterrupt:
    print("Script interrupted. Closing WebSocket connection.")
finally:
    pass  # Cleanup will be handled by atexit
    