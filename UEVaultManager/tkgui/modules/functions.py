# coding=utf-8
"""
Utilities functions and tools
These functions depend on the globals.py module and can generate circular dependencies when imported.
"""
import logging
import os
import shutil
import sys
import time
import tkinter as tk
from datetime import datetime
from io import BytesIO
from tkinter import messagebox
from typing import Optional

import requests
from PIL import Image, ImageTk
from termcolor import colored

from UEVaultManager.lfs.utils import path_join
from UEVaultManager.models.types import DateFormat
from UEVaultManager.tkgui.modules import globals as gui_g
from UEVaultManager.tkgui.modules.cls.ProgressWindowClass import ProgressWindow


def log_format_message(name: str, levelname: str, message: str) -> str:
    """
    Format the log message.
    :param name: the name of the logger.
    :param levelname: the level of log.
    :param message: the message to format.
    :return: the formatted message.
    """
    return f'[{name}] {levelname}: {message}'


def box_message(msg: str, level='info'):
    """
    Display a message box with the given message.
    :param msg: the message to display.
    :param level: the level of the message (info, warning, error).
    """
    level_lower = level.lower()
    if level_lower == 'warning':
        log_warning(msg)
        messagebox.showwarning(title=gui_g.s.app_title, message=msg)
    elif level_lower == 'error':
        messagebox.showerror(title=gui_g.s.app_title, message=msg)
        log_error(msg)
        # done in log_error
        # exit(1)
    else:
        log_info(msg)
        messagebox.showinfo(title=gui_g.s.app_title, message=msg)


def box_yesno(msg: str) -> bool:
    """
    Display a YES/NO message box with the given message.
    :param msg: the message to display .
    :return:  True if the user clicked on Yes, False otherwise.
    """
    return messagebox.askyesno(title=gui_g.s.app_title, message=msg)


def box_okcancel(msg: str) -> bool:
    """
    Display an OK/CANCEL message box with the given message.
    :param msg: the message to display.
    :return:  True if the user clicked on Yes, False otherwise.
    """
    return messagebox.askokcancel(title=gui_g.s.app_title, message=msg)


def todo_message() -> None:
    """
    Display a message box with a message saying that the feature is not implemented yet.
    """
    msg = 'Not implemented yet'
    print_msg = log_format_message(gui_g.s.app_title, 'info', colored(msg, 'yellow'))
    print(print_msg)
    messagebox.showinfo(title=gui_g.s.app_title, message=msg)


def from_cli_only_message(content='This feature is only accessible') -> None:
    """
    Display a message box with a message saying that the feature is only accessible when running the application is launched using the cli.
    """
    msg = f'{content} when this application is launched using the UEVM cli edit command.'
    print_msg = log_format_message(gui_g.s.app_title, 'info', colored(msg, 'yellow'))
    print(print_msg)
    messagebox.showinfo(title=gui_g.s.app_title, message=msg)


def log_info(msg: str) -> None:
    """
    Log an info message.
    :param msg: the message to log.

    Notes:
        It will use gui_g.UEVM_log_ref if defined, otherwise it will print the message on the console.
    """
    if gui_g.UEVM_log_ref is not None:
        gui_g.UEVM_log_ref.info(msg)
    else:
        print_msg = log_format_message(gui_g.s.app_title, 'info', colored(msg, 'blue'))
        print(print_msg)


def log_debug(msg: str) -> None:
    """
    Log a debug message.
    :param msg: the message to log.

    Notes:
        It will use gui_g.UEVM_log_ref if defined, otherwise it will print the message on the console.
        This message will only be logged if the debug mode is enabled.
    """
    if not gui_g.s.debug_mode:
        return
    if gui_g.UEVM_log_ref is not None:
        # ensure that the debug messages will be logged even if the log level not set to DEBUG in the cli
        log_level = gui_g.UEVM_log_ref.level
        if log_level == logging.DEBUG:
            gui_g.UEVM_log_ref.debug(msg)
        else:
            gui_g.UEVM_log_ref.info(msg)
    else:
        print_msg = log_format_message(gui_g.s.app_title, 'Debug', colored(msg, 'light_grey'))
        print(print_msg)


def log_warning(msg: str) -> None:
    """
    Log a warning message.
    :param msg: the message to log.

    Notes:
        It will use gui_g.UEVM_log_ref if defined, otherwise it will print the message on the console.
    """
    if gui_g.UEVM_log_ref is not None:
        gui_g.UEVM_log_ref.info(msg)
    else:
        print_msg = log_format_message(gui_g.s.app_title, 'Warning', colored(msg, 'orange'))
        print(print_msg)


def log_error(msg: str) -> None:
    """
    Log an error message.
    :param msg: the message to log.

    Notes:
        The application will (normally) exit after logging the message. Sometimes it doesn't work (check ?)
        It will use gui_g.UEVM_log_ref if defined, otherwise it will print the message on the console.
    """
    if gui_g.UEVM_log_ref is not None:
        gui_g.UEVM_log_ref.error(msg)
    else:
        print_msg = log_format_message(gui_g.s.app_title, 'Error', colored(msg, 'red', 'bold'))
        print(print_msg)
        exit_and_clean_windows()


def resize_and_show_image(image: Image, canvas: tk.Canvas, scale: float = 1.0) -> None:
    """
    Resize the given image and display it in the given canvas.
    :param image: the image to display.
    :param canvas: the canvas to display the image in.
    :param scale: the scale to apply to the image.
    """
    # Resize the image while keeping the aspect ratio
    target_height = int(gui_g.s.preview_max_height * scale)
    aspect_ratio = float(image.width * scale) / float(image.height * scale)
    target_width = int(target_height * aspect_ratio)
    resized_image = image.resize((target_width, target_height), Image.BILINEAR)
    tk_image = ImageTk.PhotoImage(resized_image)
    # Calculate center coordinates
    x = max(0, (canvas.winfo_width() - tk_image.width()) // 2)
    y = max(0, (canvas.winfo_height() - tk_image.height()) // 2)
    canvas.create_image(x, y, anchor=tk.NW, image=tk_image)
    canvas.image = tk_image


def show_asset_image(image_url: str, canvas_image=None, scale: float = 1.0, timeout=(4, 4)) -> bool:
    """
    Show the image of the given asset in the given canvas.
    :param image_url: the url of the image to display.
    :param canvas_image: the canvas to display the image in.
    :param scale: the scale to apply to the image.
    :param timeout: timeout for the request. Could be a float or a tuple of float (connect timeout, read timeout).
    :return: True if the image has been displayed, False otherwise.
    """
    if gui_g.s.offline_mode:
        # could be usefull if connexion is slow
        show_default_image(canvas_image)
        return False
    if canvas_image is None or not image_url or str(image_url) in gui_g.s.cell_is_empty_list:
        return False
    try:
        # print(image_url)
        # noinspection DuplicatedCode
        if not os.path.isdir(gui_g.s.cache_folder):
            os.mkdir(gui_g.s.cache_folder)
        image_filename = path_join(gui_g.s.cache_folder, os.path.basename(image_url))
        # Check if the image is already cached
        if os.path.isfile(image_filename) and (time.time() - os.path.getmtime(image_filename)) < gui_g.s.image_cache_max_time:
            # Load the image from the cache folder
            image = Image.open(image_filename)
        else:
            response = requests.get(image_url, timeout=timeout)
            image = Image.open(BytesIO(response.content))
            with open(image_filename, "wb") as file:
                file.write(response.content)
        resize_and_show_image(image, canvas_image, scale)
        return True
    except Exception as error:
        log_warning(f'Error showing image: {error!r}')
        gui_g.timeout_error_count += 1
        # check error timeout
        if gui_g.timeout_error_count >= 5:
            box_message(
                f'The application had {gui_g.timeout_error_count} timeout errors when loading images.\nIt is going offline to avoid been too slow.\nTo fix that, check you internet connection.\nYou can disabled offline mode in the "Show options" panel, or by restarting the application.',
                level='warning'
            )
            gui_g.timeout_error_count = 0
            gui_g.s.offline_mode = True
            return False


def show_default_image(canvas_image=None) -> None:
    """
    Show the default image in the given canvas.
    :param canvas_image: the canvas to display the image in.
    """
    if canvas_image is None:
        return
    try:
        # Load the default image
        if os.path.isfile(gui_g.s.default_image_filename):
            def_image = Image.open(gui_g.s.default_image_filename)
            # noinspection PyTypeChecker
            resize_and_show_image(def_image, canvas_image)
    except Exception as error:
        log_warning(f'Error showing default image {gui_g.s.default_image_filename} cwd:{os.getcwd()}: {error!r}')


def json_print_key_val(json_obj, indent=4, print_result=True, output_on_gui=False) -> None:
    """
    Pretty prints a JSON object in a simple 'key: value' format.
    :param json_obj:  The JSON object to print.
    :param indent: the number of spaces to indent each level.
    :param print_result: determines whether to print the result.
    :param output_on_gui: determines whether to print the result on the GUI.
    :return: the pretty printed JSON object.
    """

    def _process(obj, level=0):
        lines = []
        indent_str = ' ' * indent * level

        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(value, (dict, list)):
                    lines.append(f'{indent_str}{key}:')
                    lines.extend(_process(value, level + 1))
                else:
                    lines.append(f'{indent_str}{key}: {value}')
        elif isinstance(obj, list):
            for item in obj:
                lines.extend(_process(item, level))
        else:
            lines.append(f'{indent_str}{obj}')

        return lines

    result = '\n'.join(_process(json_obj))

    if print_result:
        if output_on_gui and gui_g.WindowsRef.display_content is not None:
            gui_g.WindowsRef.display_content.display(result)
        else:
            print(result)


def custom_print(text='', keep_mode=True) -> None:
    """
    Print the given text on the GUI if it's available, otherwise print it on the console².
    :param text: the text to print.
    :param keep_mode: whether to keep the existing content when adding a new one.
    """
    if gui_g.WindowsRef.display_content is not None:
        gui_g.WindowsRef.display_content.display(content=text, keep_mode=keep_mode)
    else:
        print(text)


def get_tk_root(container) -> Optional[tk.Tk]:
    """
    Get the root window.
    :param container:  the container window or object
    :return: the root window
    """
    if container is None:
        return None
    root = None
    # get the root window to avoid creating multiple progress windows
    try:
        # a tk window child class
        root = container.winfo_toplevel()
    except (AttributeError, tk.TclError):
        # an editableTable class
        try:
            root = container.get_container.winfo_toplevel()
        except (AttributeError, tk.TclError):
            pass
    return root


def show_progress(
    parent=None,
    text='Working...Please wait',
    width=500,
    height=120,
    max_value_l=0,
    show_progress_l=False,
    show_btn_stop_l=False,
    quit_on_close: bool = False,
    keep_existing: bool = False,
    function: callable = None,
    function_parameters: dict = None,
    force_new_window: bool = False
) -> Optional[ProgressWindow]:
    """
    Show the progress window. If the progress window does not exist, it will be created.
    :param parent: the parent window. Could be None
    :param text: the text to display in the progress window.
    :param width: the width of the progress window.
    :param height: the height of the progress window.
    :param max_value_l: the maximum value of the progress bar.
    :param show_progress_l: whether to show the progress bar.
    :param show_btn_stop_l: whether to show the stop button.
    :param quit_on_close: whether to quit the application when the window is closed.
    :param keep_existing: whether to keep the existing content when adding a new one.
    :param function: the function to execute.
    :param function_parameters: the parameters of the function.
    :param force_new_window: whether to force the creation of a new progress window.
    :return: the progress window.
    It will create a new progress window if one does not exist and update parent._progress_window
    """
    pw = None
    root = get_tk_root(parent)
    create_a_new_progress_window = force_new_window
    if not root:
        return None
    try:
        # check if a progress window already exists
        pw = root.progress_window
        if force_new_window:
            pw.close_window(True)
        else:
            pw.update()  # a call to test if the window is still active
    except (tk.TclError, AttributeError, RuntimeError):
        create_a_new_progress_window = True

    if create_a_new_progress_window:
        pw = ProgressWindow(
            title=gui_g.s.app_title,
            parent=parent,
            icon=gui_g.s.app_icon_filename,
            width=width,
            height=height,
            show_btn_stop=show_btn_stop_l,
            show_progress=show_progress_l,
            max_value=max_value_l,
            quit_on_close=quit_on_close,
            function=function,
            function_parameters=function_parameters
        )
        root.progress_window = pw
    try:
        # here the pw could have already been close if it was modal or using thhreads
        pw.set_activation(False)
        if keep_existing:
            text = pw.get_text() + '\n' + text
        pw.set_text(text)
        pw.update()
    except (tk.TclError, AttributeError):
        pw = None
        gui_g.progress_window_ref = None
    return pw


def close_progress(parent) -> None:
    """
    Close the progress window.
    :param parent: the parent window.
    It accesses to the parent.progress_window property
    """
    root = get_tk_root(parent)
    if root and root.progress_window is not None:
        root.progress_window.close_window()
        root.progress_window = None


def create_file_backup(file_src: str, logger: logging.Logger = None, path: str = '') -> str:
    """
    Create a backup of a file.
    :param file_src: path to the file to back up.
    :param logger: the logger to use to display info. Could be None.
    :param path: the path to the config folder.
    :return: the full path to the backup file.
    """
    # for files defined relatively to the config folder
    file_src = file_src.replace('~/.config', path)
    file_backup = ''
    if not file_src:
        return ''
    try:
        file_name_no_ext, file_ext = os.path.splitext(file_src)
        file_backup = f'{file_name_no_ext}_{datetime.now().strftime(DateFormat.file_suffix)}{file_ext}.BAK'
        shutil.copy(file_src, file_backup)
        if logger is not None:
            logger.info(f'File {file_src} has been copied to {file_backup}')
    except FileNotFoundError:
        if logger is not None:
            logger.info(f'File {file_src} has not been found')
    return file_backup


def update_loggers_level(logger: logging.Logger = None, debug_value=None) -> None:
    """
    Change the logger level of debug depending on the debug mode.
    :param logger: the logger
    :param debug_value: the value to set. If None, it will use the value of gui_g.s.debug_mode

    Notes:
        Will also update all the loggers level of the UEVM classes.
        Call this function when the debug mode is changed.
    """
    if logger is not None:
        if logger.name not in gui_g.UEVM_logger_names:
            gui_g.UEVM_logger_names.append(logger.name)
    debug_value = gui_g.s.debug_mode if debug_value is None else debug_value
    for logger_name in gui_g.UEVM_logger_names:
        logger = logging.getLogger(logger_name)
        logger.setLevel(level=logging.DEBUG if debug_value else logging.INFO)


def make_modal(window: tk.Toplevel = None, wait_for_close=True) -> None:
    """
    Make the given window modal.
    :param window: the window to make modal
    :param wait_for_close: whether to wait for the window to be closed before continuing
    """
    window.grab_set()
    window.focus_set()
    if wait_for_close:
        # Note: this will block the main window
        window.wait_window()


def set_widget_state(widget: tk.Widget, is_enabled: bool, text_swap: {} = None) -> None:
    """
    Enable or disable a widget.
    :param widget: widget to update.
    :param is_enabled: whether to enable the widget, if False, disable it.
    :param text_swap: dict {'normal':text, 'disabled':text} to swap the text of the widget depending on its state.
    """
    if widget is not None:
        state = tk.NORMAL if is_enabled else tk.DISABLED
        state_inversed = tk.NORMAL if not is_enabled else tk.DISABLED
        try:
            # noinspection PyUnresolvedReferences
            widget.config(state=state)
            current_text = widget.cget('text')
            if text_swap is not None and text_swap.get(state, '') == current_text:
                swapped_text = text_swap.get(state_inversed, '')
                if swapped_text:
                    # noinspection PyUnresolvedReferences
                    widget.config(text=swapped_text)
        except tk.TclError:
            pass


def enable_widget(widget) -> None:
    """
    Enable a widget.
    :param widget: widget to update.
    """
    set_widget_state(widget, True)


def disable_widget(widget) -> None:
    """
    Disable a widget.
    :param widget: widget to update.
    """
    set_widget_state(widget, False)


def set_widget_state_in_list(list_of_widget: [], is_enabled: bool, text_swap: {} = None) -> None:
    """
    Enable or disable a widget.
     :param list_of_widget: the list of widgets to update.
    :param is_enabled: whether to enable the widget, if False, disable it.
    :param text_swap: dict {'normal':text, 'disabled':text} to swap the text of the widget depending on its state.
    """
    for widget in list_of_widget:
        set_widget_state(widget, is_enabled, text_swap)


def enable_widgets_in_list(list_of_widget: []) -> None:
    """
    Enable a list of widgets.
    :param list_of_widget: the list of widgets to enable.
    """
    for widget in list_of_widget:
        enable_widget(widget)


def disable_widgets_in_list(list_of_widget: []) -> None:
    """
    Disable a list of widgets.
    :param list_of_widget: the list of widgets to disable.
    :return:
    """
    for widget in list_of_widget:
        disable_widget(widget)


def update_widgets_in_list(is_enabled: bool, list_name: str, text_swap=None) -> None:
    """
    Update the state of a list of widgets.
    :param is_enabled: true to enable the widgets, False to disable them.
    :param list_name: the name of the list of widgets to update.
    :param text_swap: dict {'normal':text, 'disabled':text} to swap the text of the widget depending on its state.
    """
    widget_list = gui_g.stated_widgets.get(list_name, [])
    set_widget_state_in_list(widget_list, is_enabled=is_enabled, text_swap=text_swap)


def exit_and_clean_windows(code: int = 1):
    """
    Exit the application and clean all the windows before.
    :return:
    """
    window_list = gui_g.WindowsRef.get_properties()
    for window in window_list:
        if window is not None:
            window.quit()
            window.destroy()
    sys.exit(code)


def check_and_convert_list_to_str(str_or_list) -> str:
    """
    Check if the given parameter is a list and convert it to a string, else return the given parameter.
    :param str_or_list: the string or list to convert.
    :return: the converted string or the given parameter.
    """
    result = str_or_list
    if type(str_or_list).__name__ in ['list', 'dict_values']:
        # if the list does not only contain strings, it will raise an error.
        # So we use map to convert all the values to string
        result = ','.join(map(str, str_or_list))
    return result
