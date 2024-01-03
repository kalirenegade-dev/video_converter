import os
import sqlite3


# Directory containing video files

#localPath
path = 'W:\TV Shows'
#folder_path = f"\\\\?\\{path}"

#networkPath
path = '\\BLUESRV\Media\TV Shows'
folder_path = f"\\\\?\\UNC{path}"



# Connect to SQLite database (or create if it doesn't exist)
conn = sqlite3.connect('videodb.db')
cursor = conn.cursor()

# Create a table to store video information
cursor.execute('''
    CREATE TABLE IF NOT EXISTS videos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        videopath TEXT NOT NULL,
        processing_state INTEGER NOT NULL
    )
''')

# Commit the changes before inserting data
conn.commit()


def has_converted_in_filename(file_path):
    _, file_name = os.path.split(file_path)
    return "-converted" in file_name

def has_checked_in_filename(file_path):
    _, file_name = os.path.split(file_path)
    return "-checked" in file_name

# Function to check if a file is a video file
def is_video_file(file_name):
    video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.wmv']
    return any(file_name.lower().endswith(ext) for ext in video_extensions)

def insert_video_data(file_path):
    # Insert video data with processing_state=0
    cursor.execute('''
        INSERT INTO videos (videopath, processing_state)
        VALUES (?, ?)
    ''', (file_path, 0))

# Recursive function to insert video files into the database
def insert_videos_in_directory(directory):
    for file_name in os.listdir(directory):
        file_path = os.path.join(directory, file_name)

        if has_converted_in_filename(file_name) or has_checked_in_filename(file_name):
            pass
        elif os.path.isfile(file_path) and is_video_file(file_name):
            insert_video_data(file_path)
        elif os.path.isdir(file_path):
            insert_videos_in_directory(file_path)

# Start the recursion
insert_videos_in_directory(folder_path)

# Commit the changes and close the connection
conn.commit()
conn.close()

print("Videos inserted into the database.")
