import subprocess
import os
import argparse

TotalSpaceSaving = 0
FileCounter = 0
force = False
append = False
recursive = False
folder_path = "."
gpu = False
logFile = 'convert.log'
cleanup = False

def parse_arguments():
    global force
    global folder_path
    global append
    global recursive
    global gpu
    global logFile
    global cleanup
    parser = argparse.ArgumentParser(description='Video conversion script with optional force flag.')
    parser.add_argument('-f', '--force', action='store_true', help='Force the conversion without asking for confirmation.')
    parser.add_argument('-a', '--append', action='store_true', help='Append to existing log file.')
    parser.add_argument('-p', '--path', type=str, help='Specify the folder path for video files.')
    parser.add_argument('-r', '--recursive', action='store_true', help='convert videos inside folders')
    parser.add_argument('-g', '--gpu', action='store_true', help='Uses Gpu by enabling the nvenc_h264 flag')
    parser.add_argument('-l', '--logfile', type=str, help='Location of log file.')
    parser.add_argument('-c', '--cleanup', action='store_true', help='Removes any failed converted files')
  
    args = parser.parse_args()
    
    # Update the force variable based on the command-line argument
    force = args.force
    folder_path = args.path or folder_path
    append = args.append
    recursive = args.recursive
    gpu = args.gpu
    logFile = args.logfile
    cleanup = args.cleanup
    
def get_video_files(folder_path):
    global recursive
    video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.ogg', '.ogv', '.m4v']
    video_files = []

    def scan_directory(directory):
        for entry in os.scandir(directory):
            if entry.is_file() and entry.name.lower().endswith(tuple(video_extensions)):
                video_files.append(entry.path)
            elif entry.is_dir() and recursive:
                scan_directory(entry.path)

    scan_directory(folder_path)
    return video_files

def get_file_size(file_path):
    try:
        # Get the size of the file in bytes
        size_bytes = os.path.getsize(file_path)
        return size_bytes / 1024
    except FileNotFoundError:
        return None

def format_size_difference(difference):
    tb = abs(difference) / (1024**4)
    gb = abs(difference) / (1024**3)
    mb = abs(difference) / 1024
    if tb >= 1:
        return f"({tb:.2f} TB)"
    elif gb >= 1:
        return f"({gb:.2f} GB)"
    else:
        return f"({mb:.2f} MB)"

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
    print(f"Difference in size: {format_size_difference(difference_bytes)}")
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
            'HandBrakeCLI.exe',
            '-Z', 'General/Very Fast 720p30',
            '-i', file_path,
            '-o', output_file_path,
        ]
        return handbrake_command
    

def ConvertFile(input_file):
    global TotalSpaceSaving
    try:
        subprocess.run(handbrake_command_gen(input_file), check=True)
        directory, file_name, file_extension = separate_path_filename_extension(input_file)
        output_file_path_converted = os.path.join(directory, file_name + '-converted' + ".mp4")
        output_file_path_Skipped = os.path.join(directory, file_name + '-skipped' + file_extension)
        print("Conversion successful")
        IsSmaller,SizeDiffrence,inbytes = is_output_smaller(input_file)
        if IsSmaller:
            print("The converted file would be smaller")
            print("Delete old video / rename new vidio")
            try:
                os.remove(input_file)
                print(f"The file '{input_file}' has been deleted successfully.")
            except FileNotFoundError:
                print(f"The file '{input_file}' does not exist.")
            except Exception as e:
                print(f"An error occurred: {e}")
            Log(f'FileName: {input_file}\nThe converted file would be smaller\nSpace Saved: {SizeDiffrence}')
            TotalSpaceSaving += inbytes
        else:
            print("The converted file would be SizeDiffrence")
            print("Delete converted video")
            try:
                os.remove(output_file_path_converted)
                print(f"The file '{output_file_path_converted}' has been deleted successfully.")
            except FileNotFoundError:
                print(f"The file '{output_file_path_converted}' does not exist.")
            except Exception as e:
                print(f"An error occurred: {e}")
            try:
                os.rename(input_file, output_file_path_Skipped)
                print(f"The file '{input_file}' has been renamed to '{input_file}' successfully.")
            except FileNotFoundError:
                print(f"The file '{input_file}' does not exist.")
            except Exception as e:
                print(f"An error occurred: {e}")
            Log(f'FileName: {input_file}\nThe converted file would be Larger by {SizeDiffrence}')
    except subprocess.CalledProcessError as e:
        print(f"Conversion failed with error code {e.returncode}")

def has_converted_in_filename(file_path):
    _, file_name = os.path.split(file_path)
    return "-converted" in file_name

def has_checked_in_filename(file_path):
    _, file_name = os.path.split(file_path)
    return "-checked" in file_name

def StartProcess(folder_path):
    global TotalSpaceSaving
    global FileCounter
    global append
    if(append):
        pass
    else:
        deleteLog()
    Log("Log file for conversion\n----------------------------\nStart of log")
    video_files = get_video_files(folder_path)
    for video_file in video_files:
        directory, file_name, file_extension = separate_path_filename_extension(video_file)
        output_file_path_converted = os.path.join(directory, file_name + '-converted' + ".mp4")
        if os.path.exists(video_file) and os.path.exists(output_file_path_converted):
            try:
                os.remove(output_file_path_converted)
                print(f"The file '{output_file_path_converted}' has been deleted successfully.")
            except FileNotFoundError:
                print(f"The file '{output_file_path_converted}' does not exist.")
            except Exception as e:
                print(f"An error occurred: {e}")
    video_files = get_video_files(folder_path)
    for video_file in video_files:
        FileCounter+=1
        os.system("title " + f"Files ({FileCounter} / {len(video_files)})  Space Saved: {format_size_difference(TotalSpaceSaving)}")
        if(force):
            print(video_file)
            Log("-------------Start----------")
            ConvertFile(video_file)
            Log("--------------End-----------")
        else:
            if(has_converted_in_filename(video_file) or has_checked_in_filename(video_file)):
                pass
            else:
                print(video_file)
                Log("-------------Start----------")
                ConvertFile(video_file)
                Log("--------------End-----------")
    Log(f"------Total Space Saved-----\n{format_size_difference(TotalSpaceSaving)}")
    
def Log(text):
    global logFile
    with open(logFile, 'a') as log_file:
        log_file.write(f'{text}\n')

def deleteLog():
    global logFile
    if os.path.exists(logFile):
        try:
            os.remove(logFile)
        except Exception as e:
            print(f"An error occurred while deleting the log file: {e}")



parse_arguments()

if(cleanup):
    deleteLog()
else:
    StartProcess(folder_path)    


