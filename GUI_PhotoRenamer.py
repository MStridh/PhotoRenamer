import PySimpleGUI as sg
import sys
import getopt
import re
import datetime
import threading

from pathlib import Path
from dataclasses import dataclass
from enum import auto

# Own lib
from processors.eventinc import process_eventinc_file


class FILE_PATTERNS:
    EVENT_INC               = "^EventInc_\d{4}-\d{2}-\d{2}\.uat\.zip$"


class TEXT:
    EMPTY                   = ""
    APPLICATION_TITLE       = "EventInc processor"
    FILE_PROCESSED          = "Processed"
    FILE_QUEUED             = "Queued"


class KEY:
    FILE_LIST               = "-FILE_LIST-"
    INC_INPUT_PATH          = "-RESULT_FILE-"
    INC_INPUT_PATH_BTN      = "-RESULT_FILE_BTN-"
    INC_OUTPUT_PATH         = "-OUTPUT_PATH-"
    INC_OUTPUT_PATH_BTN     = "-OUTPUT_PATH_BTN-"
    REQUEST_FILES_RTN       = "-REQUEST_FILES_RTN-"
    REQUEST_FILES_RESULT    = "-REQUEST_FILES_RESULT-"
    PROCESS_SEL_BTN         = "-PROCESS_SELECTED_BTN-"
    PROCESS_SEL_RESULT      = "-PROCESS_SELECTED_RESULT-"
    TABLE_STATUS            = "-TABLE_STATUS-"
    DEBUG_OUTPUT            = "-DEBUG_OUTPUT-"



def do_list_inc_files(window, inc_input_path:Path, inc_base_path:Path):
    
    inc_input_path = Path(inc_input_path)
    inc_success_path = Path(inc_base_path) / "Status" / "EventInc"

    inc_files = list()
    for inc_file in inc_input_path.iterdir():
        if re.match(FILE_PATTERNS.EVENT_INC, inc_file.name, re.IGNORECASE):
            
            inc_success_file = inc_success_path / f"{inc_file.name}.success"

            if inc_success_file.exists() \
            and inc_success_file.is_file():
                inc_files.append([inc_file.name, TEXT.FILE_PROCESSED])
            else:
                inc_files.append([inc_file.name, TEXT.EMPTY])


    # Post result event to main thread
    window.write_event_value(KEY.REQUEST_FILES_RESULT, inc_files)


def do_process_inc_files(inc_input_path:Path, inc_base_path:Path, selected_inc_files:list):
    global window

    def event_procgress_callback(inc_file, value):
        window.write_event_value(KEY.PROCESS_SEL_RESULT, [inc_file, f"{round(value * 100)}%"])

    for inc_file in selected_inc_files:
        process_eventinc_file(inc_input_path / inc_file, inc_base_path, event_procgress_callback)

        # Post result event to main thread
        window.write_event_value(KEY.PROCESS_SEL_RESULT, [inc_file, TEXT.FILE_PROCESSED])

    print("Done")    




def get_table_row_id(table_content, inc_file_name):
    for index, row in enumerate(table_content):

        # Unpack the row to needed variables
        name, *_ = row
        if name == inc_file_name:
            return index

    


def print_event_data(event, values):
    print(f'\nEvent: {event}')
    for key in values: 
        print(f'Key: {key} Value: {values[key]}')




def get_layout(def_inc_input_path, def_inc_base_path):
    # All the stuff inside your window.
    headings = [ 'File Name', 'Status' ]
    heading_widths = [60, 30]

    config_layout = [
        [
            sg.Text('EventInc source path: ', size=(13, 1)), 
            sg.InputText(def_inc_input_path, size=(100, 1), key=KEY.INC_INPUT_PATH, readonly=True, enable_events=False),
            sg.FolderBrowse(enable_events=False, key=KEY.INC_INPUT_PATH_BTN, initial_folder=def_inc_input_path)
        ],
        [
            sg.Text('ODBS Data path: ', size=(13, 1)), 
            sg.InputText(def_inc_base_path, size=(100, 1), key=KEY.INC_OUTPUT_PATH, readonly=True, enable_events=False),
            sg.FolderBrowse(enable_events=False, key=KEY.INC_OUTPUT_PATH_BTN, initial_folder=def_inc_base_path)
        ]
    ]

    actions_layout = [
        [
            sg.Button('List files', key=KEY.REQUEST_FILES_RTN), 
            sg.Button('Process selection', key=KEY.PROCESS_SEL_BTN)
        ]
    ]

    layout = [ 
        [ sg.Frame('Configuration', config_layout, key='-FRAME_CONFIG-') ],
        [ sg.Frame('Actions', actions_layout, key='-FRAME_ACTIOS-') ],
        [ sg.Table([], size=(100,30), col_widths = heading_widths, expand_x=True, headings=headings, justification='left', key=KEY.FILE_LIST, auto_size_columns=False) ],
        [sg.Text('0 file(s)', key=KEY.TABLE_STATUS)], 
        [sg.Text('Debug output: ')], 
        [sg.Output(size=(130, 6))] 
    ]

    return layout


def set_button_status(disable:bool=False):
    global window

    window[KEY.INC_INPUT_PATH_BTN].update(disabled=disable)
    window[KEY.INC_OUTPUT_PATH_BTN].update(disabled=disable)

    window[KEY.REQUEST_FILES_RTN].update(disabled=disable)
    window[KEY.PROCESS_SEL_BTN].update(disabled=disable)



def exec_app(def_inc_input_path, def_inc_base_path):
    global window


    # Create the Window
    #sg.theme('Default1')   # Add a touch of color
    #sg.theme_previewer()
    window = sg.Window(TEXT.APPLICATION_TITLE, get_layout(def_inc_input_path, def_inc_base_path), finalize=True)

    # Event Loop to process "events" and get the "values" of the inputs
    while True:
        # Read events
        event, values = window.read()


        # if user closes window break the loop
        if event == sg.WIN_CLOSED: 
            break


        # Get the file list from SJ FTP server
        elif event == KEY.REQUEST_FILES_RTN:
            """ Here the list of EventInc files are requested """

            #set_button_status(disable=True)

            if KEY.INC_INPUT_PATH not in values:
                print("No file selected")
                continue
    
            inc_input_path = values[KEY.INC_INPUT_PATH]
            inc_base_path = values[KEY.INC_OUTPUT_PATH]


            
            threading.Thread(target=do_list_inc_files, args=[window, inc_input_path, inc_base_path], daemon=True).start()                
            print(f"Looking for EventInc files")
        


        # Get the file list from SJ FTP server
        elif event == KEY.REQUEST_FILES_RESULT:

            #set_button_status(disable=False)

            selected_inc_files = sorted(values[KEY.REQUEST_FILES_RESULT], reverse=True)
            print(f"Populating file list")


            # Update table status
            window[KEY.TABLE_STATUS].update(f'{len(selected_inc_files)} file(s)')

            # Add the filtered list of files filtered on train name
            #window[KEYS.FILELIST].update(sorted(filtered_files, key=lambda item: item[1]))
            window[KEY.FILE_LIST].update(selected_inc_files)

            print(f"Done")


        elif event in KEY.PROCESS_SEL_BTN:

            # Get all selected file names (column 0) from the table
            selected_inc_files = [window[KEY.FILE_LIST].Values[idx][0] for idx in values[KEY.FILE_LIST]]

            print(f"Processing {len(selected_inc_files)} file(s)")

            # Get directories
            inc_input_path = Path(values[KEY.INC_INPUT_PATH])
            inc_base_path =  Path(values[KEY.INC_OUTPUT_PATH])
            inc_output_path = Path(values[KEY.INC_OUTPUT_PATH]) / "Project" / "SJ_X2U"
            inc_success_path = Path(values[KEY.INC_OUTPUT_PATH]) / "Status" / "EventInc"


            if not inc_output_path.exists():
                print(f"Output directory don't exists: {inc_output_path}")
                continue

            if not inc_success_path.exists():
                print(f"Success directory don't exists: {inc_success_path}")
                continue

            # Check that there are any files to download
            if len(selected_inc_files) == 0:
                print(f"No files to process")
                continue

            table_content = window[KEY.FILE_LIST].Values
            for inc_file in selected_inc_files:
                idx = get_table_row_id(table_content, inc_file)
                table_content[idx][1] = TEXT.FILE_QUEUED


            threading.Thread(target=do_process_inc_files, args=[inc_input_path, inc_base_path, selected_inc_files], daemon=True).start()                


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
    print("-i        : EventInc source folder")
    print("-o        : EventInc data folder")
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
    # Coolect all data from arguments
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


    # --------------------
    # Run EventInc processor
    # --------------------

    exec_app(def_inc_input_dir, def_inc_base_dir)
