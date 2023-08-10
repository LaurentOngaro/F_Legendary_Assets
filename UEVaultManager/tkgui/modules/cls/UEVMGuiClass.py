# coding=utf-8
"""
Implementation for:
- UEVMGui: the main window of the application.
"""
import os
import re
import shutil
import tkinter as tk
from datetime import datetime
from tkinter import filedialog as fd

from rapidfuzz import fuzz

import UEVaultManager.tkgui.modules.functions as gui_f  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.functions_no_deps as gui_fn  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience
from UEVaultManager.api.egs import GrabResult
from UEVaultManager.models.UEAssetScraperClass import UEAssetScraper
from UEVaultManager.tkgui.modules.cls.DisplayContentWindowClass import DisplayContentWindow
from UEVaultManager.tkgui.modules.cls.EditableTableClass import EditableTable
from UEVaultManager.tkgui.modules.cls.FakeProgressWindowClass import FakeProgressWindow
from UEVaultManager.tkgui.modules.comp.FilterFrameComp import FilterFrame
from UEVaultManager.tkgui.modules.comp.UEVMGuiContentFrameComp import UEVMGuiContentFrame
from UEVaultManager.tkgui.modules.comp.UEVMGuiControlFrameComp import UEVMGuiControlFrame
from UEVaultManager.tkgui.modules.comp.UEVMGuiOptionsFrameComp import UEVMGuiOptionsFrame
from UEVaultManager.tkgui.modules.comp.UEVMGuiToolbarFrameComp import UEVMGuiToolbarFrame
from UEVaultManager.tkgui.modules.functions_no_deps import set_custom_style
from UEVaultManager.tkgui.modules.types import DataSourceType, UEAssetType


def clean_ue_asset_name(name_to_clean: str) -> str:
    """
    Clean a name to remove unwanted characters.
    :param name_to_clean: name to clean.
    :return: cleaned name.
    """
    # ONE: convert some unwanted strings to @. @ is used to identify the changes made
    patterns = [
        r'UE_[\d._]+',  # any string starting with 'UE_' followed by any digit, dot or underscore ex: 'UE_4_26'
        r'_UE[\d._]+',  # any string starting with '_UE' followed by any digit, dot or underscore ex: '_UE4_26'
        r'\d+[._]+',  # at least one digit followed by a dot or underscore  ex: '1.0' or '1_0'
        ' - UE Marketplace',  # remove ' - UE Marketplace'
        r'\b(\w+)\b in (\1){1}.',
        # remove ' in ' and the string before and after ' in ' are the same ex: "Linhi Character in Characters" will keep only "Linhi"
        r' in \b.+?$',  # any string starting with ' in ' and ending with the end of the string ex: ' in Characters'
    ]
    patterns = [re.compile(p) for p in patterns]
    for pattern in patterns:
        name_to_clean = pattern.sub('@', name_to_clean)

    # TWO: remove converted string with relicats
    patterns = [
        r'[@]+\d+',  # a @ followed by at least one digit ex: '@1' or '@11'
        r'\d+[@]+',  # at least one digit followed by @ ex: '1@' or '1@@'
        r'[@]+',  # any @  ex: '@' or '@@'
    ]
    patterns = [re.compile(p) for p in patterns]
    for pattern in patterns:
        name_to_clean = pattern.sub('', name_to_clean)

    name_to_clean = name_to_clean.replace('_', '-')
    return name_to_clean.strip()  # Remove leading and trailing spaces


class UEVMGui(tk.Tk):
    """
    This class is used to create the main window for the application.
    :param title: The title.
    :param icon: The icon.
    :param screen_index: The screen index where the window will be displayed.
    :param data_source: The source where the data is stored or read from.
    :param data_source_type: The type of data source (DataSourceType.FILE or DataSourceType.SQLITE).
    :param show_open_file_dialog: If True, the open file dialog will be shown at startup.
    """
    editable_table: EditableTable = None
    progress_window: FakeProgressWindow = None
    _toolbar_frame: UEVMGuiToolbarFrame = None
    _control_frame: UEVMGuiControlFrame = None
    _options_frame: UEVMGuiOptionsFrame = None
    _content_frame: UEVMGuiContentFrame = None
    _filter_frame: FilterFrame = None
    egs = None

    def __init__(
        self,
        title: str = 'UVMEGUI',
        icon='',
        screen_index: int = 0,
        data_source_type: DataSourceType = DataSourceType.FILE,
        data_source=None,
        show_open_file_dialog: bool = False,
        rebuild_data: bool = False,
    ):
        super().__init__()
        self.data_source_type = data_source_type
        if data_source_type == DataSourceType.SQLITE:
            show_open_file_dialog = False
        self.title(title)
        self.style = set_custom_style(gui_g.s.theme_name, gui_g.s.theme_font)
        width: int = gui_g.s.width
        height: int = gui_g.s.height
        x_pos: int = gui_g.s.x_pos
        y_pos: int = gui_g.s.y_pos
        if not (x_pos and y_pos):
            x_pos, y_pos = gui_fn.get_center_screen_positions(screen_index, width, height)
        self.geometry(f'{width}x{height}+{x_pos}+{y_pos}')
        gui_fn.set_icon_and_minmax(self, icon)
        self.resizable(True, True)
        pack_def_options = {'ipadx': 5, 'ipady': 5, 'padx': 3, 'pady': 3}

        content_frame = UEVMGuiContentFrame(self)
        self._content_frame = content_frame
        self.core = None if gui_g.UEVM_cli_ref is None else gui_g.UEVM_cli_ref.core

        # gui_g.UEVM_gui_ref = self  # important ! Must be donne before any use of a ProgressWindow. If not, an UEVMGuiHiddenRootClass will be created and the ProgressWindow still be displayed after the init
        # reading from CSV file version
        # self.editable_table = EditableTable(container=content_frame, data_source=data_source, rows_per_page=36, show_statusbar=True)

        # reading from database file version
        self.editable_table = EditableTable(
            container=content_frame,
            data_source_type=data_source_type,
            data_source=data_source,
            rows_per_page=36,
            show_statusbar=True,
            update_page_numbers_func=self.update_navigation,
            update_rows_text_func=self.update_rows_text
        )
        self.editable_table.set_preferences(gui_g.s.datatable_default_pref)
        self.editable_table.show()
        self.editable_table.resize_columns()  # must be done once, after the whole init of the EditableTable
        self.editable_table.update()

        toolbar_frame = UEVMGuiToolbarFrame(self, self.editable_table)
        self._toolbar_frame = toolbar_frame
        control_frame = UEVMGuiControlFrame(self, self.editable_table)
        self._control_frame = control_frame
        options_frame = UEVMGuiOptionsFrame(self)
        self._options_frame = options_frame

        toolbar_frame.pack(**pack_def_options, fill=tk.X, side=tk.TOP, anchor=tk.NW)
        content_frame.pack(**pack_def_options, fill=tk.BOTH, side=tk.LEFT, anchor=tk.NW, expand=True)
        control_frame.pack(**pack_def_options, fill=tk.BOTH, side=tk.RIGHT, anchor=tk.NW)
        # not displayed at start
        # _options_frame.pack(**pack_def_options, fill=tk.BOTH, side=tk.RIGHT, anchor=tk.NW)

        self.bind('<Key>', self.on_key_press)
        # Bind the table to the mouse motion event
        self.editable_table.bind('<Motion>', self.on_mouse_over_cell)
        self.editable_table.bind('<Leave>', self.on_mouse_leave_cell)
        self.editable_table.bind('<<CellSelectionChanged>>', self.on_selection_change)
        self.protocol('WM_DELETE_WINDOW', self.on_close)

        if not show_open_file_dialog and (rebuild_data or self.editable_table.must_rebuild):
            if gui_f.box_yesno('Data file is invalid or empty. Do you want to rebuild data from sources files ?'):
                if not self.editable_table.rebuild_data():
                    gui_f.log_error('Rebuild data error. This application could not run without a file to read from or some data to build from it')
                    self.destroy()  # self.quit() won't work here
                    return
            elif data_source_type == DataSourceType.FILE and gui_f.box_yesno(
                'So, do you want to load another file ? If not, the application will be closed'
            ):
                show_open_file_dialog = True
            else:
                self.destroy()  # self.quit() won't work here
                gui_f.log_error('No valid source to read data from. Application will be closed', )

        if show_open_file_dialog:
            if self.open_file() == '':
                gui_f.log_error('This application could not run without a file to read data from')
                self.quit()
        # Quick edit the first row
        self.editable_table.update_quick_edit(0)
        if gui_g.s.data_filters:
            self.load_filters(gui_g.s.data_filters)

        show_option_fist = False  # debug_only
        if show_option_fist:
            self.toggle_options_panel(True)
            self.toggle_actions_panel(False)

    def mainloop(self, n=0):
        """
        Mainloop method
        Overrided to add loggin function for debugging
        """
        gui_f.log_info(f'starting mainloop in {__name__}')
        self.tk.mainloop(n)
        gui_f.log_info(f'ending mainloop in {__name__}')

    def _open_file_dialog(self, save_mode=False, filename=None) -> str:
        """
        Open a file dialog to choose a file to save or load data to/from.
        :param save_mode: if True, the dialog will be in saving mode, else in loading mode.
        :param filename: the default filename to use.
        :return: the chosen filename.
        """
        # adding category to the default filename
        if not filename:
            filename = gui_g.s.default_filename
        initial_dir = os.path.dirname(filename)
        default_filename = os.path.basename(filename)  # remove dir
        default_ext = os.path.splitext(default_filename)[1]  # get extension
        default_filename = os.path.splitext(default_filename)[0]  # get filename without extension
        try:
            # if the file is empty or absent or invalid when creating the class, the filter_frame is not defined
            category = self._filter_frame.category
        except AttributeError:
            category = None
        if category and category != gui_g.s.default_value_for_all:
            default_filename = default_filename + '_' + category + default_ext
        else:
            default_filename = default_filename + default_ext
        if save_mode:
            filename = fd.asksaveasfilename(
                title='Choose a file to save data to', initialdir=initial_dir, filetypes=gui_g.s.data_filetypes, initialfile=default_filename
            )
        else:
            filename = fd.askopenfilename(
                title='Choose a file to read data from', initialdir=initial_dir, filetypes=gui_g.s.data_filetypes, initialfile=default_filename
            )
        return filename

    def _change_navigation_state(self, state: str) -> None:
        """
        Change the state of the navigation buttons.
        :param state: 'normal' or 'disabled'.
        """
        self._toolbar_frame.btn_first_page.config(state=state)
        self._toolbar_frame.btn_prev_page.config(state=state)
        self._toolbar_frame.btn_next_page.config(state=state)
        self._toolbar_frame.btn_last_page.config(state=state)
        self._toolbar_frame.entry_current_page.config(state=state)

    def _check_and_get_widget_value(self, tag):
        """
        Check if the widget with the given tags exists and return its value and itself.
        :param tag: tag of the widget that triggered the event.
        :return: value,widget.
        """
        if tag == '':
            return None, None
        widget = self._control_frame.lbtf_quick_edit.get_child_by_tag(tag)
        if widget is None:
            gui_f.log_warning(f'Could not find a widget with tag {tag}')
            return None, None
        col = widget.col
        row = widget.row
        if col is None or row is None or col < 0 or row < 0:
            gui_f.log_debug(f'invalid values for row={row} and col={col}')
            return None, widget
        value = widget.get_content()
        return value, widget

    def on_key_press(self, event) -> None:
        """
        Handle key press events.
        :param event:
        """
        if event.keysym == 'Escape':
            if gui_g.edit_cell_window_ref:
                gui_g.edit_cell_window_ref.quit()
                gui_g.edit_cell_window_ref = None
            elif gui_g.edit_row_window_ref:
                gui_g.edit_row_window_ref.quit()
                gui_g.edit_row_window_ref = None
            else:
                self.on_close()
        # elif event.keysym == 'Return':
        #    self.editable_table.create_edit_record_window()

    def on_mouse_over_cell(self, event=None) -> None:
        """
        Show the image of the asset when the mouse is over the cell.
        :param event:
        """
        if event is None:
            return
        canvas_image = self._control_frame.canvas_image
        try:
            row_index: int = self.editable_table.get_row_clicked(event)
            self.update_rows_text(row_index)
            image_url = self.editable_table.get_image_url(row_index)
            gui_f.show_asset_image(image_url=image_url, canvas_image=canvas_image)
        except IndexError:
            gui_f.show_default_image(canvas_image)

    def on_mouse_leave_cell(self, _event=None) -> None:
        """
        Show the default image when the mouse leaves the cell.
        :param _event:
        """
        self.update_rows_text()
        canvas_image = self._control_frame.canvas_image
        gui_f.show_default_image(canvas_image=canvas_image)

    def on_selection_change(self, event=None) -> None:
        """
        When the selection changes, show the selected row in the quick edit frame.
        :param event:
        """
        row_index: int = self.editable_table.get_row_index_with_offet(event.widget.currentrow)
        self.editable_table.update_quick_edit(row_index)

    def on_entry_current_page_changed(self, _event=None) -> None:
        """
        When the page number changes, show the corresponding page.
        :param _event:
        """
        page_num = 1
        try:
            page_num = self._toolbar_frame.entry_current_page.get()
            page_num = int(page_num)
            gui_f.log_debug(f'showing page {page_num}')
            self.editable_table.current_page = page_num
            self.editable_table.update()
        except (ValueError, UnboundLocalError) as error:
            gui_f.log_error(f'could not convert page number {page_num} to int. {error!r}')

    # noinspection PyUnusedLocal
    def on_quick_edit_focus_out(self, event=None, tag='') -> None:
        """
        When the focus leaves a quick edit widget, save the value.
        :param event: ignored but required for an event handler.
        :param tag: tag of the widget that triggered the event.
        """
        value, widget = self._check_and_get_widget_value(tag)
        if widget:
            self.editable_table.quick_edit_save_value(row_index=widget.row, col_index=widget.col, value=value, tag=tag)

    # noinspection PyUnusedLocal
    def on_quick_edit_focus_in(self, event=None, tag='') -> None:
        """
        When the focus enter a quick edit widget, check (and clean) the value.
        :param event: ignored but required for an event handler.
        :param tag: tag of the widget that triggered the event.
        """
        value, widget = self._check_and_get_widget_value(tag=tag)
        # empty the widget if the value is the default value or none
        if widget and (value == 'None' or value == widget.default_content or value == gui_g.s.empty_cell):
            value = ''
            widget.set_content(value)

    # noinspection PyUnusedLocal
    def on_switch_edit_flag(self, event=None, tag='') -> None:
        """
        When the focus leaves a quick edit widget, save the value.
        :param event: event that triggered the call.
        :param tag: tag of the widget that triggered the event.
        """
        _, widget = self._check_and_get_widget_value(tag)
        if widget:
            value = widget.switch_state(event=event)
            self.editable_table.quick_edit_save_value(row_index=widget.row, col_index=widget.col, value=value, tag=tag)

    def on_close(self, _event=None) -> None:
        """
        When the window is closed, check if there are unsaved changes and ask the user if he wants to save them.
        :param _event: the event that triggered the call of this function.
        """
        if self.editable_table is not None and self.editable_table.must_save:
            if gui_f.box_yesno('Changes have been made. Do you want to save them in the source file ?'):
                self.save_all(show_dialog=False)  # will save the settings too
        self.close_window()  # will save the settings too

    def close_window(self) -> None:
        """
        Close the window.
        """
        self.save_settings()
        self.quit()

    def save_settings(self) -> None:
        """
        Save the settings of the window.
        :return:
        """
        if gui_g.s.reopen_last_file:
            gui_g.s.last_opened_file = self.editable_table.data_source
        # store window geometry in config settings
        gui_g.s.width = self.winfo_width()
        gui_g.s.height = self.winfo_height()
        gui_g.s.x_pos = self.winfo_x()
        gui_g.s.y_pos = self.winfo_y()
        column_infos = {}
        for index, col in enumerate(self.editable_table.model.df.columns):  # df.model checked
            column_infos[col] = {}
            column_infos[col]['width'] = self.editable_table.columnwidths.get(col, -1)  # -1 means default width. Still save the value to
            column_infos[col]['pos'] = index
        sorted_cols_by_pos = dict(sorted(column_infos.items(), key=lambda item: item[1]['pos']))
        gui_g.s.column_infos = sorted_cols_by_pos
        gui_g.s.save_config_file()

    def open_file(self) -> str:
        """
        Open a file and Load data from it.
        :return: the name of the file that was loaded.
        """
        data_table = self.editable_table
        filename = self._open_file_dialog(filename=data_table.data_source)
        if filename and os.path.isfile(filename):
            data_table.data_source = filename
            if data_table.valid_source_type(filename):
                if not data_table.load_data():
                    gui_f.box_message('Error when loading data')
                    return filename
                data_table.current_page = 1
                data_table.update()
                self.update_navigation()
                self.update_data_source()
                gui_f.box_message(f'The data source {filename} as been read')
                return filename
            else:
                gui_f.box_message('Operation cancelled')

    def save_all(self, show_dialog=True) -> str:
        """
        Save the data to the current data source.
        :param show_dialog: if True, show a dialog to select the file to save to, if False, use the current file.
        :return: the name of the file that was saved.
        """
        self.save_settings()

        if self.editable_table.data_source_type == DataSourceType.FILE:
            if show_dialog:
                filename = self._open_file_dialog(filename=self.editable_table.data_source, save_mode=True)
                if filename:
                    self.editable_table.data_source = filename
            else:
                filename = self.editable_table.data_source
            if filename:
                self.editable_table.save_data()
                self.update_data_source()
            return filename
        else:
            self.editable_table.save_data()
            return ''

    def export_selection(self) -> None:
        """
        Export the selected rows to a file.
        """
        # Get selected row indices
        selected_rows = self.editable_table.get_selected_rows()
        if len(selected_rows):
            filename = self._open_file_dialog(save_mode=True, filename=self.editable_table.data_source)
            if filename:
                selected_rows.to_csv(filename, index=False)
                gui_f.box_message(f'Selected rows exported to "{filename}"')
        else:
            gui_f.box_message('Select at least one row first')

    def add_row(self, row_data=None) -> None:
        """
        Add a new row at the current position.
        :param row_data: data to add to the row.
        """
        self.editable_table.create_row(row_data=row_data, add_to_existing=True)
        self.editable_table.must_save = True
        self.editable_table.update()

    def del_row(self) -> None:
        """
        Remove the selected row from the DataFrame.
        """
        # if self.editable_table.pagination_enabled and gui_f.box_yesno('To delete a row, The pagination must be disabled. Do you want to disable it now ?'):
        #     self.toggle_pagination(forced_value=False)
        #     return
        self.editable_table.del_row()

    def search_for_url(self, folder: str, parent: str, check_if_valid=False) -> str:
        """
        Search for a marketplace_url file that matches a folder name in a given folder.
        :param folder: name to search for.
        :param parent: parent folder to search in.
        :param check_if_valid: if True, check if the marketplace_url is valid. Return an empty string if not.
        :return: the marketplace_url found in the file or an empty string if not found.
        """

        def read_from_url_file(entry, folder_name, returned_urls: [str]) -> bool:
            """
            Read an url from a .url file and add it to the list of urls to return.
            :param entry: the entry to process.
            :param folder_name: the name of the folder to search for.
            :param returned_urls: a list of urls to return. We use a list instead of a str because we need to modify it from the inner function.
            :return: True if the entry is a file and the name matches the folder name, False otherwise.
            """
            if entry.is_file() and entry.name.lower().endswith('.url'):
                folder_name_cleaned = clean_ue_asset_name(folder_name)
                file_name = os.path.splitext(entry.name)[0]
                file_name_cleaned = clean_ue_asset_name(file_name)
                fuzz_score = fuzz.ratio(folder_name_cleaned, file_name_cleaned)
                gui_f.log_debug(f'Fuzzy compare {folder_name} ({folder_name_cleaned}) with {file_name} ({file_name_cleaned}): {fuzz_score}')
                minimal_score = gui_g.s.minimal_fuzzy_score_by_name.get('default', 70)
                for key, value in gui_g.s.minimal_fuzzy_score_by_name.items():
                    key = key.lower()
                    if key in folder_name_cleaned.lower() or key in file_name_cleaned.lower():
                        minimal_score = value
                        break

                if fuzz_score >= minimal_score:
                    with open(entry.path, 'r') as f:
                        for line in f:
                            if line.startswith('URL='):
                                returned_urls[0] = line.replace('URL=', '').strip()
                                return True
            return False

        if self.core is None:
            return ''
        egs = self.core.egs
        read_urls = ['']
        entries = os.scandir(parent)
        if any(read_from_url_file(entry, folder, read_urls) for entry in entries):
            found_url = read_urls[0]
        else:
            found_url = egs.get_marketplace_product_url(asset_slug=clean_ue_asset_name(folder))
        if check_if_valid and egs is not None and not egs.is_valid_url(found_url):
            found_url = ''

        return found_url

    def scan_folders(self) -> None:
        """
        Scan the folders to find files that can be loaded.
        """
        valid_folders = {}
        invalid_folders = []
        folder_to_scan = gui_g.s.folders_to_scan

        if self.core is None:
            gui_f.from_cli_only_message('URL Scraping and scanning features are only accessible')

        pw = gui_f.show_progress(self, text='Scanning folders for new assets', width=500, height=120, show_progress_l=False)

        while folder_to_scan:
            full_folder = folder_to_scan.pop()
            full_folder_abs = os.path.abspath(full_folder)
            folder_name = os.path.basename(full_folder_abs)
            parent_folder = os.path.dirname(full_folder_abs)
            folder_name_lower = folder_name.lower()

            msg = f'Scanning folder {full_folder}'
            gui_f.log_info(msg)
            if not pw.update_and_continue(value=0, text=f'Scanning folder:\n{gui_fn.shorten_text(full_folder, 30)}'):
                gui_f.close_progress(self)
                return

            if os.path.isdir(full_folder):
                if self.core.scan_assets_logger:
                    self.core.scan_assets_logger.info(msg)

                folder_is_valid = folder_name_lower in gui_g.s.ue_valid_folder_content
                parent_could_be_valid = folder_name_lower in gui_g.s.ue_invalid_folder_content or folder_name_lower in gui_g.s.ue_possible_folder_content

                if folder_is_valid:
                    folder_name = os.path.basename(parent_folder)
                    parent_folder = os.path.dirname(parent_folder)
                    path = os.path.dirname(full_folder_abs)
                    pw.set_text(f'{folder_name} as a valid folder.\nChecking asset url...')
                    pw.update()
                    msg = f'-->Found {folder_name} as a valid project'
                    gui_f.log_info(msg)
                    marketplace_url = self.search_for_url(folder=folder_name, parent=parent_folder, check_if_valid=False)
                    grab_result = ''
                    if marketplace_url:
                        grab_result = GrabResult.NO_ERROR.name if self.core.egs.is_valid_url(marketplace_url) else GrabResult.NO_RESPONSE.name
                    valid_folders[folder_name] = {
                        'path': path,
                        'asset_type': UEAssetType.Asset,
                        'marketplace_url': marketplace_url,
                        'grab_result': grab_result
                    }
                    if self.core.scan_assets_logger:
                        self.core.scan_assets_logger.info(msg)
                    continue
                elif parent_could_be_valid:
                    # the parent folder contains some UE folders but with a bad structure
                    content_folder_name = 'Content'
                    if gui_f.box_yesno(
                        f'The folder {parent_folder} seems to be a valid UE folder but with a bad structure. Do you want to move all its subfolders inside a "{content_folder_name}" subfolder ?'
                    ):
                        content_folder = os.path.join(parent_folder, content_folder_name)
                        if not os.path.isdir(content_folder):
                            os.makedirs(content_folder, exist_ok=True)
                            for entry in os.scandir(parent_folder):
                                if entry.name != content_folder_name:
                                    path = entry.path
                                    shutil.move(path, content_folder)
                                    if path in folder_to_scan:
                                        folder_to_scan.remove(path)
                        msg = f'-->Found {parent_folder}. The folder has been restructured as a valid project'
                        gui_f.log_debug(msg)
                        if full_folder in folder_to_scan:
                            folder_to_scan.remove(full_folder)
                        if parent_folder not in folder_to_scan:
                            folder_to_scan.append(parent_folder)

                try:
                    for entry in os.scandir(full_folder):
                        entry_is_valid = entry.name.lower() not in gui_g.s.ue_invalid_folder_content
                        if entry.is_file():
                            extension_lower = os.path.splitext(entry.name)[1].lower()
                            filename_lower = os.path.splitext(entry.name)[0].lower()
                            # check if full_folder contains a "data" sub folder
                            if filename_lower == 'manifest' or extension_lower in gui_g.s.ue_valid_file_content:
                                path = full_folder_abs
                                has_valid_folder_inside = any(
                                    os.path.isdir(os.path.join(full_folder, folder_inside)) for folder_inside in gui_g.s.ue_valid_manifest_content
                                )
                                if filename_lower == 'manifest':
                                    if has_valid_folder_inside:
                                        asset_type = UEAssetType.Manifest
                                        # we need to move to parent folder to get the real names because manifest files are inside a specific sub folder
                                        folder_name = os.path.basename(parent_folder)
                                        parent_folder = os.path.dirname(parent_folder)
                                        path = os.path.dirname(full_folder_abs)
                                    else:
                                        asset_type = UEAssetType.Asset
                                        gui_f.log_warning(
                                            f'{full_folder_abs} has a manifest file but no data folder.It will be considered as an asset'
                                        )
                                else:
                                    asset_type = UEAssetType.Plugin if extension_lower == '.uplugin' else UEAssetType.Asset

                                marketplace_url = self.search_for_url(folder=folder_name, parent=parent_folder, check_if_valid=False)
                                grab_result = ''
                                if marketplace_url:
                                    grab_result = GrabResult.NO_ERROR.name if self.core.egs.is_valid_url(
                                        marketplace_url
                                    ) else GrabResult.NO_RESPONSE.name
                                valid_folders[folder_name] = {
                                    'path': path,
                                    'asset_type': asset_type,
                                    'marketplace_url': marketplace_url,
                                    'grab_result': grab_result
                                }
                                msg = f'-->Found {folder_name} as a valid project containing a {asset_type.name}' if extension_lower in gui_g.s.ue_valid_file_content else f'-->Found {folder_name} containing a {asset_type.name}'
                                gui_f.log_debug(msg)
                                if self.core.scan_assets_logger:
                                    self.core.scan_assets_logger.info(msg)
                                if grab_result != GrabResult.NO_ERROR.name or not marketplace_url:
                                    invalid_folders.append(folder_name)
                                # remove all the subfolders from the list of folders to scan
                                folder_to_scan = [folder for folder in folder_to_scan if not folder.startswith(full_folder_abs)]
                                continue

                        # add subfolders to the list of folders to scan
                        elif entry.is_dir() and entry_is_valid:
                            folder_to_scan.append(entry.path)
                except FileNotFoundError:
                    gui_f.log_debug(f'{full_folder_abs} has been removed during the scan')

            # sort the list to have the parent folder POPED (by the end) before the subfolders
            folder_to_scan = sorted(folder_to_scan, key=lambda x: len(x), reverse=True)

        msg = '\n\nValid folders found after scan:\n'
        gui_f.log_info(msg)
        if self.core.scan_assets_logger:
            self.core.scan_assets_logger.info(msg)
        date_added = datetime.now().strftime(gui_g.s.csv_datetime_format)
        row_data = {'Date added': date_added, 'Creation date': date_added, 'Update date': date_added, 'Added manually': True}
        data = self.editable_table.get_data()  # get_data checked
        count = len(valid_folders.items())
        pw.reset(new_text='Scraping data and adding assets to the table', new_max_value=count)
        pw.show_progress_bar()
        pw.update()
        row_added = 0
        for name, content in valid_folders.items():
            if not pw.update_and_continue(increment=1, text=f'Adding {name}'):
                break
            marketplace_url = content['marketplace_url']
            gui_f.log_info(f'{name} : a {content["asset_type"].name} at {content["path"]} with marketplace_url {marketplace_url} ')
            # set default values for the row, some will be replaced by Scraping
            row_data.update(
                {
                    'App name': name,
                    'Category': content['asset_type'].category_name,
                    'Origin': content['path'],
                    'Url': content['marketplace_url'],
                    'Grab result': content['grab_result'],
                    'Added manually': True,
                }
            )
            row_index = -1
            try:
                # get the indexes if value already exists in column 'Origin' for a pandastable
                rows_serie = data.loc[lambda x: x['Origin'].str.lower() == content['path'].lower()]
                row_indexes = rows_serie.index
                if len(row_indexes) > 0:
                    row_index = row_indexes[0]
                    gui_f.log_info(f"An existing row at index {row_index} has been found with path {content['path']}")
            except (IndexError, ValueError) as error:
                gui_f.log_warning(f'Error when checking the existence for {name} at {content["path"]}: error {error!r}')
                invalid_folders.append(content["path"])
                continue
            if row_index == -1:
                self.editable_table.create_row(row_data=row_data, add_to_existing=True)
                row_index = 0  # added at the start of the table. As it, the index is always known
                row_added += 1
            forced_data = {
                # 'category': content['asset_type'].category_name,
                'origin': content['path'],
                'asset_url': content['marketplace_url'],
                'grab_result': content['grab_result'],
                'added_manually': True,
            }
            if content['grab_result'] == GrabResult.NO_ERROR.name:
                self.scrap_row(marketplace_url=marketplace_url, row_index=row_index, forced_data=forced_data, show_message=False)
            else:
                self.editable_table.update_row(row_index=row_index, ue_asset_data=forced_data)

                # self.editable_table.resetIndex(drop=False)
        pw.hide_progress_bar()
        pw.hide_stop_button()
        pw.set_text('Updating the table. Could take a while...')
        pw.update()
        gui_f.close_progress(self)

        if invalid_folders:
            result = '\n'.join(invalid_folders)
            result = f'The following folders have produce invalid results during the scan:\n{result}'
            if gui_g.display_content_window_ref is None:
                gui_g.display_content_window_ref = DisplayContentWindow(title='UEVM: status command output', quit_on_close=False)
                gui_g.display_content_window_ref.display(result)
            gui_f.log_warning(result)

    def _scrap_from_url(self, marketplace_url: str, forced_data=None, show_message=False):
        asset_data = None
        # check if the marketplace_url is a marketplace marketplace_url
        ue_marketplace_url = self.core.egs.get_marketplace_product_url()
        if ue_marketplace_url.lower() in marketplace_url.lower():
            # get the data from the marketplace marketplace_url
            asset_data = self.core.egs.get_asset_data_from_marketplace(marketplace_url)
            if asset_data is None or asset_data.get('grab_result', None) != GrabResult.NO_ERROR.name or not asset_data.get('id', ''):
                msg = f'Unable to grab data from {marketplace_url}'
                gui_f.log_warning(msg)
                if show_message:
                    gui_f.box_message(msg)
                return None
            api_product_url = self.core.egs.get_api_product_url(asset_data['id'])
            scraper = UEAssetScraper(
                start=0,
                assets_per_page=1,
                max_threads=1,
                store_in_db=True,
                store_in_files=True,
                store_ids=False,  # useless for now
                load_from_files=False,
                engine_version_for_obsolete_assets=self.core.engine_version_for_obsolete_assets,
                egs=self.core.egs  # VERY IMPORTANT: pass the EGS object to the scraper to keep the same session
            )
            scraper.get_data_from_url(api_product_url)
            asset_data = scraper.scraped_data.pop()  # returns a list of one element
            if forced_data is not None:
                for key, value in forced_data.items():
                    asset_data[0][key] = value
            scraper.asset_db_handler.set_assets(asset_data)
        else:
            msg = f'The asset url {marketplace_url} is invalid and could not be scrapped for this row'
            gui_f.log_warning(msg)
            if show_message:
                gui_f.box_message(msg)
        return asset_data

    def scrap_row(self, marketplace_url: str = None, row_index: int = None, forced_data=None, show_message=True):
        """
        Scrap the data for the current row or a given marketplace_url.
        :param marketplace_url: marketplace_url to scrap.
        :param row_index: row index to scrap.
        :param forced_data: if not None, all the key in forced_data will replace the scrapped data
        :param show_message: if True, show a message if the marketplace_url is not valid
        """

        if self.core is None:
            gui_f.from_cli_only_message('URL Scraping and scanning features are only accessible')
            return

        row_indexes = self.editable_table.multiplerowlist

        if marketplace_url is None and row_indexes is None and len(row_indexes) < 1:
            if show_message:
                gui_f.box_message('You must select a row first')
            return
        row_count = len(row_indexes)
        pw = None
        if marketplace_url is None:
            base_text = 'Scraping assets data. Could take a while...'
            if row_count > 1:
                pw = gui_f.show_progress(
                    self, text=base_text, max_value_l=row_count, width=450, height=150, show_progress_l=True, show_stop_button_l=True
                )
            for row_index in row_indexes:
                row_index: int = self.editable_table.get_row_index_with_offet(row_index)
                row_data = self.editable_table.get_row(row_index, return_as_dict=True)
                marketplace_url = row_data['Url']
                text = base_text + f'\n Row {row_index}: scraping {gui_fn.shorten_text(marketplace_url)}'
                if pw and not pw.update_and_continue(increment=1, text=text):
                    gui_f.close_progress(self)
                    return
                asset_data = self._scrap_from_url(marketplace_url, forced_data=forced_data, show_message=show_message)
                if asset_data is not None:
                    self.editable_table.update_row(row_index=row_index, ue_asset_data=asset_data)
                    if show_message and row_count == 1:
                        gui_f.box_message(f'Data for row {row_index} have been updated from the marketplace')

            gui_f.close_progress(self)
            if show_message and row_count >= 1:
                gui_f.box_message(f'All Datas for {row_count} rows have been updated from the marketplace')
        else:
            asset_data = self._scrap_from_url(marketplace_url, forced_data=forced_data, show_message=show_message)
            self.editable_table.update_row(row_index=row_index, ue_asset_data=asset_data)

    def load_filters(self, filters=None):
        """
        Load the filters from a dictionary.
        :param filters: filters.
        """
        if filters is None:
            return
        try:
            self._filter_frame.load_filters(filters)
            # self.update_navigation() # done in load_filters and inner calls
        except Exception as error:
            gui_f.log_error(f'Error loading filters: {error!r}')

    def toggle_pagination(self, forced_value=None) -> None:
        """
        Toggle pagination. Will change the navigation buttons states when pagination is changed.
        :param forced_value: if not None, will force the pagination to the given value.
        """
        if forced_value is not None:
            self.editable_table.pagination_enabled = forced_value
        else:
            self.editable_table.pagination_enabled = not self.editable_table.pagination_enabled
        self.editable_table.update()
        if not self.editable_table.pagination_enabled:
            # Disable prev/next buttons when pagination is disabled
            self._change_navigation_state(tk.DISABLED)
            self._toolbar_frame.btn_toggle_pagination.config(text='Enable  Pagination')
        else:
            self.update_navigation()  # will also update buttons status
            self._toolbar_frame.btn_toggle_pagination.config(text='Disable Pagination')

    def show_first_page(self) -> None:
        """
        Show the first page of the table.
        """
        self.editable_table.first_page()
        self.update_navigation()

    def show_prev_page(self) -> None:
        """
        Show the previous page of the table.
        """
        self.editable_table.prev_page()
        self.update_navigation()

    def show_next_page(self) -> None:
        """
        Show the next page of the table.
        """
        self.editable_table.next_page()
        self.update_navigation()

    def show_last_page(self) -> None:
        """
        Show the last page of the table.
        """
        self.editable_table.last_page()
        self.update_navigation()

    def prev_asset(self) -> None:
        """
        Move to the previous asset in the table.
        """
        self.editable_table.move_to_prev_record()

    def next_asset(self) -> None:
        """
        Move to the next asset in the table.
        """
        self.editable_table.move_to_next_record()

    # noinspection DuplicatedCode
    def toggle_actions_panel(self, force_showing=None) -> None:
        """
        Toggle the visibility of the Actions panel.
        :param force_showing: if True, will force showing the actions panel, if False, will force hiding it.If None, will toggle the visibility.
        """
        if force_showing is None:
            force_showing = not self._control_frame.winfo_ismapped()
        if force_showing:
            self._control_frame.pack(side=tk.RIGHT, fill=tk.BOTH)
            self._toolbar_frame.btn_toggle_controls.config(text='Hide Actions')
            self._toolbar_frame.btn_toggle_options.config(state=tk.DISABLED)
        else:
            self._control_frame.pack_forget()
            self._toolbar_frame.btn_toggle_controls.config(text='Show Actions')
            self._toolbar_frame.btn_toggle_options.config(state=tk.NORMAL)

    # noinspection DuplicatedCode
    def toggle_options_panel(self, force_showing=None) -> None:
        """
        Toggle the visibility of the Options panel.
        :param force_showing: if True, will force showing the options panel, if False, will force hiding it.If None, will toggle the visibility.
        """
        # noinspection DuplicatedCode
        if force_showing is None:
            force_showing = not self._options_frame.winfo_ismapped()
        if force_showing:
            self._options_frame.pack(side=tk.RIGHT, fill=tk.BOTH)
            self._toolbar_frame.btn_toggle_options.config(text='Hide Options')
            self._toolbar_frame.btn_toggle_controls.config(state=tk.DISABLED)
        else:
            self._options_frame.pack_forget()
            self._toolbar_frame.btn_toggle_options.config(text='Show Options')
            self._toolbar_frame.btn_toggle_controls.config(state=tk.NORMAL)

    def update_navigation(self) -> None:
        """
        Update the page numbers in the toolbar.
        """
        if self._toolbar_frame is None:
            # toolbar not created yet
            return
        current_page = self.editable_table.current_page
        total_pages = self.editable_table.total_pages
        self._toolbar_frame.entry_current_page_var.set(current_page)
        self._toolbar_frame.lbl_page_count.config(text=f' / {total_pages}')
        # enable all buttons by default
        self._change_navigation_state(tk.NORMAL)

        if not self.editable_table.pagination_enabled:
            self._toolbar_frame.entry_current_page.config(state=tk.NORMAL)
        if current_page <= 1:
            self._toolbar_frame.btn_first_page.config(state=tk.DISABLED)
            self._toolbar_frame.btn_prev_page.config(state=tk.DISABLED)
        if current_page >= total_pages:
            self._toolbar_frame.btn_next_page.config(state=tk.DISABLED)
            self._toolbar_frame.btn_last_page.config(state=tk.DISABLED)

    def update_data_source(self) -> None:
        """
        Update the data source name in the control frame.
        """
        self._control_frame.var_entry_data_source_name.set(self.editable_table.data_source)
        self._control_frame.var_entry_data_source_type.set(self.editable_table.data_source_type.name)

    def update_category_var(self) -> dict:
        """
        Update the category variable with the current categories in the data.
        :return: a dict with the new categories list as value and the key is the name of the variable.
        """
        try:
            # if the file is empty or absent or invalid when creating the class, the data is empty, so no categories
            categories = list(self.editable_table.get_data()['Category'].cat.categories)  # get_data checked
        except (AttributeError, TypeError, KeyError):
            categories = []
        categories.insert(0, gui_g.s.default_value_for_all)
        try:
            # if the file is empty or absent or invalid when creating the class, the data is empty, so no categories
            grab_results = list(self.editable_table.get_data()['Grab result'].cat.categories)  # get_data checked
        except (AttributeError, TypeError, KeyError):
            grab_results = []
        grab_results.insert(0, gui_g.s.default_value_for_all)
        return {'categories': categories, 'grab_results': grab_results}

    def update_rows_text(self, row_index=None):
        """
        Set the text to display in the preview frame about the number of rows.
        """
        if self._control_frame is None:
            return
        row_count_filtered = self.editable_table.current_count
        row_count = self.editable_table.data_count
        row_text = f'| {row_count} rows count' if row_count_filtered == row_count else f'| {row_count_filtered} filtered count | {row_count} rows count'
        if row_index is not None:
            row_offset = (self.editable_table.current_page - 1) * self.editable_table.rows_per_page + 1
            self._control_frame.lbt_image_preview.config(text=f'Image Preview for row {row_index + row_offset} {row_text}')
        else:
            self._control_frame.lbt_image_preview.config(text=f'No Image Preview {row_text}')

    def reload_data(self) -> None:
        """
        Reload the data from the data source.
        """
        if not self.editable_table.must_save or (
            self.editable_table.must_save and gui_f.box_yesno('Changes have been made, they will be lost. Are you sure you want to continue ?')
        ):
            if self.editable_table.reload_data():
                # self.update_page_numbers() done in reload_data
                self.update_category_var()
                gui_f.box_message(f'Data Reloaded from {self.editable_table.data_source}')
            else:
                gui_f.box_message(f'Failed to reload data from {self.editable_table.data_source}')

    def rebuild_data(self) -> None:
        """
        Rebuild the data from the data source. Will ask for confirmation before rebuilding.
        """
        if gui_f.box_yesno(f'The process will change the content of the windows.\nAre you sure you want to continue ?'):
            if self.editable_table.rebuild_data():
                self.update_navigation()
                self.update_category_var()
                gui_f.box_message(f'Data rebuilt from {self.editable_table.data_source}')

    def run_uevm_command(self, command_name='') -> None:
        """
        Execute a cli command and display the result in DisplayContentWindow.
        :param command_name: the name of the command to execute.
        """
        if command_name == '':
            return
        if gui_g.UEVM_cli_ref is None:
            gui_f.from_cli_only_message()
            return
        row_index: int = self.editable_table.getSelectedRow()
        app_name = self.editable_table.get_cell(row_index, self.editable_table.get_col_index('App name'))
        # gui_g.UEVM_cli_args['offline'] = True  # speed up some commands DEBUG ONLY
        # set default options for the cli command to execute
        gui_g.UEVM_cli_args['gui'] = True  # mandatory for displaying the result in the DisplayContentWindow

        # arguments for several commands
        gui_g.UEVM_cli_args['csv'] = False  # mandatory for displaying the result in the DisplayContentWindow
        gui_g.UEVM_cli_args['tcsv'] = False  # mandatory for displaying the result in the DisplayContentWindow
        gui_g.UEVM_cli_args['json'] = False  # mandatory for displaying the result in the DisplayContentWindow

        # arguments for cleanup command
        # now set in command options
        # gui_g.UEVM_cli_args['delete_extra_data'] = True
        # gui_g.UEVM_cli_args['delete_metadata'] = True

        # arguments for help command
        gui_g.UEVM_cli_args['full_help'] = True
        if app_name != '':
            gui_g.UEVM_cli_args['app_name'] = app_name

        if gui_g.display_content_window_ref is None or not gui_g.display_content_window_ref.winfo_viewable():
            # we display the window only if it is not already displayed
            function_to_call = getattr(gui_g.UEVM_cli_ref, command_name)
            function_to_call(gui_g.UEVM_cli_args)

    # noinspection PyUnusedLocal
    def open_asset_url(self, event=None) -> None:
        """
        Open the asset URL (Wrapper).
        """
        url, widget = self._check_and_get_widget_value(tag='Url')
        if url:
            self.editable_table.open_asset_url(url=url)
