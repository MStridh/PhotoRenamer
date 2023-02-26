import PySimpleGUI as sg
import sys
import getopt
import re
import threading
import shutil
import concurrent.futures
import os

from exif import Image
from pathlib import Path
from dataclasses import dataclass


class FILE_PATTERNS:
    PHOTO               = ["^.*\.JPG$", "^.*\.PNG$"]


class TEXT:
    EMPTY                   = ""
    APPLICATION_TITLE       = "Photo Renamer"
    FILE_PROCESSED          = "Processed"
    FILE_QUEUED             = "Queued"


class KEY:
    FILE_LIST               = "-FILE_LIST-"
    PHOTO_INPUT_PATH          = "-RESULT_FILE-"
    PHOTO_INPUT_PATH_BTN      = "-RESULT_FILE_BTN-"
    PHOTO_OUTPUT_PATH         = "-OUTPUT_PATH-"
    PHOTO_OUTPUT_PATH_BTN     = "-OUTPUT_PATH_BTN-"
    REQUEST_FILES_BTN       = "-REQUEST_FILES_BTN-"
    COPYORMOVE_OPTION       = "-COPYORMOVE_OPTION-"
    REQUEST_FILES_RESULT    = "-REQUEST_FILES_RESULT-"
    PROCESS_SEL_BTN         = "-PROCESS_SELECTED_BTN-"
    PROCESS_ALL_BTN         = "-PROCESS_ALL_BTN-"
    PROCESS_SEL_RESULT      = "-PROCESS_SELECTED_RESULT-"
    TABLE_STATUS            = "-TABLE_STATUS-"
    DEBUG_OUTPUT            = "-DEBUG_OUTPUT-"



def do_list_photos(photo_input_path:Path, photo_out_path:Path):
    global base_path
    photo_input_path = Path(photo_input_path)
    
    photos = list()
    for photo in photo_input_path.iterdir():
        if photo.is_dir():
            somePhotos = do_list_photos(photo, photo_out_path)
            photos.extend(somePhotos)
        for file_type in FILE_PATTERNS.PHOTO:
            if re.match(file_type, photo.name, re.IGNORECASE):
                photos.append([photo.__str__()[len(base_path) + 1:], TEXT.EMPTY])
                break

    return photos


def do_process_photos(photos_input_path:Path, photos_base_path:Path, selected_photos_files:list, action):
    global window

    for photo in selected_photos_files:
        with open(photos_input_path.__str__() + "\\" + photo,'rb') as image:
            try:
                photoTaken = Image(image).datetime.replace(":", "-") + "." + photo.split(".")[-1]
            except:
                print("No data when photo was taken for photo " + photo)
                continue
        newPhoto = photos_base_path.__str__() + "\\" + photoTaken
        oldPhoto = photos_input_path.__str__() + "\\" + photo
        if action == "Copy and rename":
            shutil.copy2(oldPhoto, newPhoto, follow_symlinks=True)
        elif action == "Move and rename":
            shutil.move(oldPhoto, newPhoto)

        # Post result event to main thread
        window.write_event_value(KEY.PROCESS_SEL_RESULT, [photo, TEXT.FILE_PROCESSED])

    print("Done")    




def get_table_row_id(table_content, photo_file_name):
    for index, row in enumerate(table_content):

        # Unpack the row to needed variables
        name, *_ = row
        if name == photo_file_name:
            return index

    


def print_event_data(event, values):
    print(f'\nEvent: {event}')
    for key in values: 
        print(f'Key: {key} Value: {values[key]}')




def get_layout(def_photo_input_path, def_photo_result_path):
    # All the stuff inside your window.
    headings = [ 'File Name', 'Status' ]
    heading_widths = [60, 30]

    config_layout = [
        [
            sg.Text('Photo source path: ', size=(14, 1)), 
            sg.InputText(def_photo_input_path, size=(100, 1), key=KEY.PHOTO_INPUT_PATH, readonly=True, enable_events=False),
            sg.FolderBrowse(enable_events=False, key=KEY.PHOTO_INPUT_PATH_BTN, initial_folder=def_photo_input_path)
        ],
        [
            sg.Text('Resulting path: ', size=(14, 1)), 
            sg.InputText(def_photo_result_path, size=(100, 1), key=KEY.PHOTO_OUTPUT_PATH, readonly=True, enable_events=False),
            sg.FolderBrowse(enable_events=False, key=KEY.PHOTO_OUTPUT_PATH_BTN, initial_folder=def_photo_result_path)
        ]
    ]

    actions_layout = [
        [
            sg.Button('List photos', key=KEY.REQUEST_FILES_BTN), 
            sg.Button('Rename selection', key=KEY.PROCESS_SEL_BTN),
            sg.Button('Rename all', key=KEY.PROCESS_ALL_BTN),
        ]
    ]
    options_layout = [
        [
            sg.Combo(['Copy and rename', 'Move and rename'], default_value = 'Copy and rename', readonly = True, key=KEY.COPYORMOVE_OPTION)
        ]
    ]

    layout = [ 
        [ sg.Frame('Configuration', config_layout, key='-FRAME_CONFIG-') ],
        [ sg.Frame('Actions', actions_layout, key='-FRAME_ACTIOS-') ],
        [ sg.Frame('Options', options_layout, key='-FRAME_OPTIONS-') ],
        [ sg.Table([], size=(100,30), col_widths = heading_widths, expand_x=True, headings=headings, justification='left', key=KEY.FILE_LIST, auto_size_columns=False) ],
        [sg.Text('0 file(s)', key=KEY.TABLE_STATUS)], 
        [sg.Text('Debug output: ')], 
        [sg.Output(size=(130, 6))] 
    ]

    return layout


def set_button_status(disable:bool=False):
    global window

    window[KEY.PHOTO_INPUT_PATH_BTN].update(disabled=disable)
    window[KEY.PHOTO_OUTPUT_PATH_BTN].update(disabled=disable)

    window[KEY.REQUEST_FILES_BTN].update(disabled=disable)
    window[KEY.PROCESS_SEL_BTN].update(disabled=disable)
    window[KEY.PROCESS_ALL_BTN].update(disabled=disable)



def exec_app(def_photo_input_path, def_photo_result_path):
    global window
    global base_path

    # Create the Window
    #sg.theme('Default1')   # Add a touch of color
    #sg.theme_previewer()
    window = sg.Window(TEXT.APPLICATION_TITLE, get_layout(def_photo_input_path, def_photo_result_path), finalize=True)

    # Event Loop to process "events" and get the "values" of the inputs
    while True:
        # Read events
        event, values = window.read()
        base_path = values[KEY.PHOTO_INPUT_PATH]


        # if user closes window break the loop
        if event == sg.WIN_CLOSED: 
            break


        # Get the photo list
        elif event == KEY.REQUEST_FILES_BTN:
            """ Here the list of photos are requested """

            #set_button_status(disable=True)

            if KEY.PHOTO_INPUT_PATH not in values:
                print("No file selected")
                continue
    
            photo_input_path = values[KEY.PHOTO_INPUT_PATH]
            photo_out_path = values[KEY.PHOTO_OUTPUT_PATH]


            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(do_list_photos, photo_input_path, photo_out_path)
                photos = future.result()
            
            # Post result event to main thread
            window.write_event_value(KEY.REQUEST_FILES_RESULT, photos)              
            print(f"Looking for photos")
        


        # Get the photo list
        elif event == KEY.REQUEST_FILES_RESULT:

            #set_button_status(disable=False)

            selected_photos = sorted(values[KEY.REQUEST_FILES_RESULT], reverse=True)
            print(f"Populating file list")


            # Update table status
            window[KEY.TABLE_STATUS].update(f'{len(selected_photos)} file(s)')

            # Add the filtered list of files filtered on train name
            window[KEY.FILE_LIST].update(selected_photos)

            print(f"Done")


        elif event in KEY.PROCESS_SEL_BTN:

            # Get all selected file names (column 0) from the table
            selected_photos = [window[KEY.FILE_LIST].Values[idx][0] for idx in values[KEY.FILE_LIST]]

            print(f"Processing {len(selected_photos)} file(s)")

            # Get directories
            photo_input_path = Path(values[KEY.PHOTO_INPUT_PATH])
            photo_output_path = Path(values[KEY.PHOTO_OUTPUT_PATH])

            if not photo_output_path.exists():
                print(f"Output directory doesn't exist: {photo_output_path}")
                continue

            # Check that there are any photos to rename
            if len(selected_photos) == 0:
                print(f"No files to process")
                continue

            threading.Thread(target=do_process_photos, args=[photo_input_path, photo_output_path, selected_photos, values[KEY.COPYORMOVE_OPTION]], daemon=True).start()     
                   
        elif event in KEY.PROCESS_ALL_BTN:

            # Get all file names from the table
            all_photos = [window[KEY.FILE_LIST].Values[idx][0] for idx in range(len(window[KEY.FILE_LIST].Values))]

            print(f"Processing {len(all_photos)} file(s)")

            # Get directories
            photo_input_path = Path(values[KEY.PHOTO_INPUT_PATH])
            photo_output_path = Path(values[KEY.PHOTO_OUTPUT_PATH])

            if not photo_output_path.exists():
                print(f"Output directory doesn't exist: {photo_output_path}")
                continue

            # Check that there are any photos to rename
            if len(all_photos) == 0:
                print(f"No files to process")
                continue

            threading.Thread(target=do_process_photos, args=[photo_input_path, photo_output_path, all_photos, values[KEY.COPYORMOVE_OPTION]], daemon=True).start()  

        elif event == KEY.PROCESS_SEL_RESULT:

            table_content = window[KEY.FILE_LIST].Values
            update_file, progress_value = values[KEY.PROCESS_SEL_RESULT]

            idx = get_table_row_id(table_content, update_file)

            if table_content[idx][1] == progress_value:
                continue

            table_content[idx][1] = progress_value
                
            current_selection = window[KEY.FILE_LIST].SelectedRows
            window[KEY.FILE_LIST].update(table_content, select_rows=current_selection)

            # Refresh the window
            window.Refresh()


        elif event == KEY.DEBUG_OUTPUT:
            print(values[KEY.DEBUG_OUTPUT])

        else: 
            print_event_data(event, values)


    window.close()



def print_help(app_name):
    """ This function prints the help/usage text to the console """

    print("usage: {} [options]".format(app_name))
    print("Options:")
    print("-i        : Photo source folder")
    print("-o        : Photo data folder")
    print("-h        : help")



if __name__ == "__main__":

    # --------------------
    # Init of needed objcts
    # --------------------

    def_inc_input_dir = None
    def_inc_base_dir = None


    # --------------------
    # Parse input
    # --------------------

    try:
        opts, args = getopt.getopt(sys.argv[1:], "hi:o:")
    except getopt.GetoptError as err:
        print("Incorrect options")  
        print("{}\n".format(err)) # will print something like "option -a not recognized"

        # print help information and exit:
        print_help(sys.argv[0])
        input("Press any key to continue.")
        sys.exit(2)



    # --------------------
    # Collect all data from arguments
    # --------------------

    for option, value in opts:
        if option == "-i":
            def_inc_input_dir = Path(value)
        
        elif option == "-o":
            def_inc_base_dir = Path(value)
        
        elif option == "-h":
            print_help(sys.argv[0])
            sys.exit(0)
        
        else:
            print("Unhandled options")
            print_help(sys.argv[0])
            input("Press any key to continue.")
            sys.exit(0)

    if def_inc_input_dir == None:
        def_inc_input_dir = os.getcwd()
    if def_inc_base_dir == None:
        def_inc_base_dir = os.getcwd()

    # --------------------
    # Run Photo renamer
    # --------------------

    exec_app(def_inc_input_dir, def_inc_base_dir)
