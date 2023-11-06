# coding=utf-8
"""
Implementation for:
- FilterFrame class: frame that contains widgets for filtering a DataFrame.
"""
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, Optional

import pandas as pd

import UEVaultManager.tkgui.modules.functions as gui_f  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience
from UEVaultManager.tkgui.modules.cls.FilterCallableClass import FilterCallable
from UEVaultManager.tkgui.modules.cls.FilterValueClass import FilterValue
from UEVaultManager.tkgui.modules.types import FilterType


# not needed here
# warnings.filterwarnings('ignore', category=FutureWarning)  # Avoid the FutureWarning when PANDAS use ser.astype(object).apply()


class FilterFrame(ttk.LabelFrame):
    """
    A frame that contains widgets for filtering a DataFrame.
    :param container: container widget.
    :param df: DataFrame to be filtered. It is not modified.
    :param update_func: function that updates the table.
    :param save_query_func: function that save the filters.
    :param load_query_func: function that load the filters.
    :param title: title of the frame.
    """

    def __init__(
        self,
        container: tk,
        df: pd.DataFrame,
        update_func: Callable,
        save_query_func: Callable = None,
        load_query_func: Callable = None,
        title: str = 'Define view filters for the data table',
    ):
        if container is None:
            raise ValueError('container can not be None')
        if update_func is None:
            raise ValueError('update_func can not be None')
        super().__init__(container, text=title)
        self._df: pd.DataFrame = df
        self._loaded_filter: Optional[FilterValue] = None
        self._quick_filters: Optional[FilterValue] = None
        self._var_entry_query = tk.StringVar()
        self.pack_def_options = {'ipadx': 2, 'ipady': 2, 'padx': 2, 'pady': 2, 'fill': tk.X, 'expand': True}
        self.grid_def_options = {'ipadx': 1, 'ipady': 1, 'padx': 1, 'pady': 1, 'sticky': tk.W}
        self.cb_quick_filter = None
        self.btn_apply_filters = None
        self.btn_clear_filter = None
        self.container = container
        self.update_func = update_func
        self.load_filter_func = load_query_func
        self.save_filter_func = save_query_func
        self.old_entry_query = ''
        self.callable: FilterCallable = FilterCallable(self._df)
        self._quick_filters = self.callable.create_dynamic_filters()
        self._create_widgets()

    @property
    def loaded_filter(self) -> Optional[FilterValue]:
        """ Return the loaded filter. """
        return self._loaded_filter

    def _search_combobox(self, _event, combobox) -> None:
        """
        Search for the text in the Combobox's values.
        :param _event: event that triggered the search.
        :param combobox: Combobox to search in.
        """
        # Get the current text in the Combobox
        text_lower = combobox.get().lower()
        if len(text_lower) < 3:
            return
        for value in combobox['values']:
            if value.lower().startswith(text_lower):
                combobox.set(value)
                self.update_controls()
                break

    # noinspection DuplicatedCode
    def _create_widgets(self) -> None:
        """
        Create filter widgets inside the FilterFrame instance.
        """
        # new row
        cur_row = 0
        cur_col = 0
        ttk_item = ttk.Label(self, text='Select quick filter')
        ttk_item.grid(row=cur_row, column=cur_col, **self.grid_def_options)
        cur_col += 1
        ttk_item = ttk.Label(self, text='Or Write a text query using column names')
        ttk_item.grid(row=cur_row, column=cur_col, columnspan=5, **self.grid_def_options)
        # new row
        cur_row += 1
        cur_col = 0
        self.cb_quick_filter = ttk.Combobox(self, values=list(self._quick_filters.keys()), state='readonly', width=20)
        self.cb_quick_filter.grid(row=cur_row, column=cur_col, **self.grid_def_options)
        self.cb_quick_filter.bind('<<ComboboxSelected>>', lambda event: self.get_quick_filter())
        self.cb_quick_filter.bind('<KeyRelease>', lambda event: self._search_combobox(event, self.cb_quick_filter))
        cur_col += 1
        self._var_entry_query = tk.StringVar()
        self.entry_query = ttk.Entry(self, textvariable=self._var_entry_query, width=40)
        self.entry_query.bind("<KeyRelease>", self._on_query_change)  # keyup
        self.entry_query.grid(row=cur_row, column=cur_col, columnspan=5, **self.grid_def_options)
        # new row
        cur_row += 1
        cur_col = 1
        self.btn_apply_filters = ttk.Button(self, text='Apply', command=self.apply_filters)
        self.btn_apply_filters.grid(row=cur_row, column=cur_col, **self.grid_def_options)
        cur_col += 1
        self.btn_view_filter = ttk.Button(self, text='View', command=self.view_filter)
        self.btn_view_filter.grid(row=cur_row, column=cur_col, **self.grid_def_options)
        cur_col += 1
        self.btn_clear_filter = ttk.Button(self, text='Clear', command=self.clear_filter)
        self.btn_clear_filter.grid(row=cur_row, column=cur_col, **self.grid_def_options)
        if self.save_filter_func is not None:
            cur_col += 1
            self.btn_save_filter = ttk.Button(self, text='Save', command=self._save_filter)
            self.btn_save_filter.grid(row=cur_row, column=cur_col, **self.grid_def_options)
        if self.load_filter_func is not None:
            cur_col += 1
            self.btn_load_filter = ttk.Button(self, text='Load', command=self._load_filter)
            self.btn_load_filter.grid(row=cur_row, column=cur_col, **self.grid_def_options)
        self.update_controls()

    def _on_query_change(self, _event) -> None:
        """
        Event handler for the query string entry.
        :param _event: event that triggered the search.
        """
        if self._var_entry_query.get() != self.old_entry_query:
            self.old_entry_query = self._var_entry_query.get()
            self.update_controls()

    def _load_filter(self) -> None:
        """
        Get the loaded filter from a file (Wrapper)
        """
        filter_values: FilterValue = self.load_filter_func()
        self.create_filter(filter_values)  # used instead if set_filter() to check if the filter is callable
        self.update_controls()

    def _save_filter(self) -> None:
        """
        Set the loaded filter to a file (Wrapper)
        """
        self.save_filter_func(self._loaded_filter)

    def set_filter(self, filter_values: FilterValue, forced_value: str = '') -> None:
        """
        Set the loaded filter.
        :param filter_values: filter values to set.
        :param forced_value: value to set in the query string entry. If empty, the value from filter_values will be used.
        """
        if not forced_value:
            forced_value = filter_values.value
        self._loaded_filter = filter_values
        self.old_entry_query = self._var_entry_query.get()
        self._var_entry_query.set(forced_value)
        self.cb_quick_filter.set('')

    def create_filter(self, filter_value: FilterValue = None) -> None:
        """
        Set the current filter from a filter_value.
        :param filter_value: filter value to set. If None, a filter value will be created from query string entry.
        """
        if not filter_value:
            # create a filter value from the query string entry
            query_string = self._var_entry_query.get()
            ftype = FilterType.STR
            filter_value = FilterValue(name='filter_loaded', value=query_string, ftype=ftype)
        # check if the filter_value is a callable and fix its ftype
        func_name, func_params = gui_f.parse_callable(filter_value.value)
        method = self.callable.get_method(func_name)
        if method is None:
            filter_value.ftype = FilterType.STR
        else:
            filter_value.ftype = FilterType.CALLABLE
        self.set_filter(filter_value)

    def update_controls(self) -> None:
        """
        Update the state of the controls based on the current state of the filters.
        """
        # Note:
        # No need to use the global widgets list here beceause this frame is meant to be "standalone" and its widgets are not used elsewhere.

        # controls always enables
        state = tk.NORMAL
        self.btn_load_filter['state'] = state
        self.btn_save_filter['state'] = state  # empty filters can be saved to remove existing one in config

        query_string = self._var_entry_query.get()
        quick_filter_name = self.cb_quick_filter.get()
        cond1 = query_string or quick_filter_name
        state = tk.NORMAL if cond1 else tk.DISABLED
        self.btn_apply_filters['state'] = state
        self.btn_view_filter['state'] = state
        self.btn_clear_filter['state'] = state

    def query_has_changed(self) -> bool:
        """
        Check if the query string has changed.
        :return: True if the query string has changed, False otherwise.
        """
        return self.old_entry_query != self._var_entry_query.get()

    def apply_filters(self) -> None:
        """
        Applie the filters and updates the caller.
        """
        quick_filter = self.get_quick_filter(only_return_filter=True)
        if quick_filter:
            self.set_filter(quick_filter)
        elif self._var_entry_query.get():
            self.create_filter()
            self.cb_quick_filter.set('')
        self.update_controls()
        self.update_func(reset_page=True)  # will call self.create_mask() and self.get_query()

    def clear_filter(self) -> None:
        """
        Reset all filter conditions and update the caller.
        """
        self.cb_quick_filter.set('')
        self._var_entry_query.set('')
        self._loaded_filter = None
        gui_g.s.save_config_file()
        if self._var_entry_query.get() != self.old_entry_query:
            self.update_controls()
            self.update_func(reset_page=True)

    def view_filter(self) -> None:
        """
        View the filter dictionary.
        """
        values = self._loaded_filter.__repr__()
        msg = values + '\n\nCopy values into clipboard ?'
        if messagebox.askyesno('View applied filter on datatable', message=msg):
            self.clipboard_clear()
            self.clipboard_append(values)

    def get_quick_filter(self, only_return_filter=False) -> FilterValue:
        """
        Get the filter value from the quick filter combobox.
        :param only_return_filter: wether only return the filter string without applying it.
        :return: a FilterValue object.
        """
        quick_filter_name = self.cb_quick_filter.get()
        quick_filter = self._quick_filters.get(quick_filter_name, None)
        if quick_filter:
            self.set_filter(quick_filter)
            if not only_return_filter:
                # self.create_mask(filter_dict.items()) # done in the line bellow
                self.update_func(reset_page=True)
            self.update_controls()
        return quick_filter

    def get_filtered_df(self)->Optional[pd.DataFrame] :
        """
        Get the filtered dataframe.
        :return: the filtered data or None if no filter is defined.
        """
        if self.loaded_filter:
            try:
                ftype: FilterType = self.loaded_filter.ftype
                filter_value = self.loaded_filter.value
                if ftype == FilterType.CALLABLE and filter_value:
                    # filter_value is a string with a function to call and some parameters
                    # that returns a mask (boolean Series)
                    func_name, func_params = gui_f.parse_callable(filter_value)
                    # get the method to call from the callable class
                    method = self.callable.get_method(func_name)
                    if method is None:
                        raise AttributeError(f'Could not find the method {func_name} in the class {self.callable.__class__.__name__}')
                    # noinspection PyUnusedLocal
                    mask_from_callable = method(*func_params)
                    query = '@mask_from_callable'  # with pandas, we can pass a reference to a mask to execute a query !!!!
                else:
                    query = filter_value
                if query:
                    return self._df.query(query)
            except (AttributeError, ):
                # print(f'Error with defined filters. Updating filter...')
                self.clear_filter()
                return None
