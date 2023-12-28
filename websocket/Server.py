import asyncio
import websockets
import json
import sqlite3
import os
TotalSpaceSaved = 0

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

# Connect to SQLite database (or create if it doesn't exist)
conn = sqlite3.connect('videodb.db')

# Create a cursor object to execute SQL queries
cursor = conn.cursor()
max_processing_state_count = 0

counter = 0
def get_max_processing_state_count():
    cursor.execute('''
        SELECT COUNT(*) FROM videos
        WHERE processing_state = 0 or processing_state = 1
    ''')
    return cursor.fetchone()[0]
    
def get_QueueCount():
    cursor.execute('''
        SELECT COUNT(*) FROM videos
        WHERE processing_state = 1
    ''')
    return cursor.fetchone()[0]
def separate_path_filename_extension(file_path):
    # Split the file path into directory, base name, and extension
    directory, file_name_with_extension = os.path.split(file_path)
    # Split the base name and extension
    file_name, file_extension = os.path.splitext(file_name_with_extension)
    return directory, file_name, file_extension
    
    
    
    
def MarkReset(video_id):
        cursor.execute('''
            UPDATE videos
            SET processing_state = 0
            WHERE id = ?
        ''', (video_id,))
        conn.commit()
        
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

def MarkConverted(FileName,video_id):
        cursor.execute('''
            UPDATE videos
            SET processing_state = 2, videopath = ?
            WHERE id = ?
        ''', (FileName,video_id,))
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
        # Update processing sta te to 1
        MarkProcessing(video_id)

        #print(f"Processing state updated to 1 for Video ID: {video_id}")
        return(videopath, video_id)

    else:
        print("No video with processing_state=0 found")
        return(None, None)

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


async def handle_websocket(websocket, path):
    global TotalSpaceSaved
    global counter
    #print(f"Client connected to {path}")
    
    try:
        # Wait for messages from the client
        async for message in websocket:
            #print(f"Received message: {message}")

            try:
                # Parse the JSON message
                data = json.loads(message)
                
                if "FileName" in data and "error" in data:
                    FileName = data["FileName"]
                    video_id = data["video_id"]
                    error = data["error"]
                    
                    
                    if (error == 'incomplete'):
                        print(f"{bcolors.FAIL}error: {error}, video_id: {video_id}, FileName: {FileName}{bcolors.ENDC}")
                        MarkReset(video_id)
                        QueueCount = get_QueueCount()
                        os.system("title " + f"({counter}/{max_processing_state_count}) Space Saved: {format_size_difference(TotalSpaceSaved)} Queue: {QueueCount}")
                    if (error == 'InvalidVideo'):
                        print(f"{bcolors.FAIL}error: {error}, video_id: {video_id}, FileName: {FileName}{bcolors.ENDC}")
                        MarkInvalid(video_id)
                        counter += 1
                        QueueCount = get_QueueCount()
                        os.system("title " + f"({counter}/{max_processing_state_count}) Space Saved: {format_size_difference(TotalSpaceSaved)} Queue: {QueueCount}")
                    if (error == 'NotFound'):
                        print(f"{bcolors.WARNING}error: {error}, video_id: {video_id}, FileName: {FileName}{bcolors.ENDC}")
                        MarkNotFound(video_id)
                        counter += 1
                        QueueCount = get_QueueCount()
                        os.system("title " + f"({counter}/{max_processing_state_count}) Space Saved: {format_size_difference(TotalSpaceSaved)} Queue: {QueueCount}")
                    
                if "FileName" in data and "SpaceSaved" in data:
                    FileName = data["FileName"]
                    SpaceSaved = data["SpaceSaved"]
                    video_id = data["video_id"]
                    print(f"{bcolors.OKGREEN}SpaceSaved: {format_size_difference(SpaceSaved)}, video_id: {video_id}, FileName: {FileName}{bcolors.ENDC}")
                    MarkConverted(FileName,video_id)
                    TotalSpaceSaved += SpaceSaved
                    counter += 1
                    QueueCount = get_QueueCount()
                    os.system("title " + f"({counter}/{max_processing_state_count}) Space Saved: {format_size_difference(TotalSpaceSaved)} Queue: {QueueCount}")        
 
                # Process the message based on its content
                if "command" in data and "ServerIdentity" in data:
                    ServerIdentity = data["ServerIdentity"]
                    print(f"{bcolors.OKBLUE}New Video Requested from ServerIdentity: {ServerIdentity}{bcolors.ENDC}")
                    if data["command"] == "RequestVideo":
                        VideoPath, video_id = getVideo()
                        if(VideoPath != None):
                            newVideoPath = VideoPath
                            directory, file_name, file_extension = separate_path_filename_extension(VideoPath)
                            print(f"{bcolors.OKBLUE}Sending {ServerIdentity} video: '{file_name + file_extension}', VideoID: {video_id}{bcolors.ENDC}")
                            #print(newVideoPath)
                            response_data = {"ServerIdentity": data["ServerIdentity"], "VideoPath": newVideoPath,"video_id": video_id}
                            response_message = json.dumps(response_data, indent=2)
                            QueueCount = get_QueueCount()
                            os.system("title " + f"({counter}/{max_processing_state_count}) Space Saved: {format_size_difference(TotalSpaceSaved)} Queue: {QueueCount}")
                            await websocket.send(response_message)
                        else:
                            #print('No Files to convert')
                            response_data = {"ServerIdentity": data["ServerIdentity"], "VideoPath": None, "video_id" : None}
                            response_message = json.dumps(response_data, indent=2)
                            await websocket.send(response_message)
                    else:
                        # Handle other commands if needed
                        pass
                else:
                    # Handle invalid or unexpected messages
                    pass

            except json.JSONDecodeError:
                print("Invalid JSON format")

    except websockets.exceptions.ConnectionClosed:
        pass
        #print("Client disconnected")

# Set up the WebSocket server
start_server = websockets.serve(handle_websocket, "0.0.0.0", 8765)  # Use "0.0.0.0" to accept connections from any IP

max_processing_state_count = get_max_processing_state_count()
QueueCount = get_QueueCount()
os.system("title " + f"({counter}/{max_processing_state_count}) Space Saved: {format_size_difference(TotalSpaceSaved)} Queue: {QueueCount}")  

# Run the server
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
conn.commit()
conn.close()