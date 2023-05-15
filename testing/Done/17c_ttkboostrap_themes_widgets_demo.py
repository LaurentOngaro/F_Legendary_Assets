import tkinter as tk
from tkinter import ttk
import ttkbootstrap as ttk
from tkinter.font import nametofont

themes_list = (
    "cosmo", "flatly", "litera", "minty", "lumen", "sandstone", "yeti", "pulse", "united", "morph", "journal", "simplex", "cerculean", "darkly",
    "superhero", "solar", "cyborg", "vapor"
)


class StyledText(tk.Text):
    """
    A text widget with a custom style.
    Text Style properties are copied from the current style ttk widgets.
    """

    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)

        style = ttk.Style(self._root().style.theme_use())
        bg_color = style.lookup('TEntry', 'fieldbackground', default='white')
        fg_color = style.lookup('TEntry', 'foreground', default='black')
        border_color = style.lookup('TEntry', 'bordercolor', default='black')
        relief = style.lookup('TEntry', 'relief', default='flat')
        font = self.get_default_font(style)
        # print(f'Default font: {font}, bg_color: {bg_color}, fg_color: {fg_color}, border_color: {border_color}, font: {font}, relief: {relief}')
        self.configure(background=bg_color, foreground=fg_color, borderwidth=1, relief=relief, font=font)

    def get_default_font(self, style=None):
        """
        Get the default font for ttk widgets. If the default font is not found, use the TkDefaultFont.
        :param style: ttk.Style object. If None, the current theme is used.
        :return: The default font for ttk widgets.
        """
        if style is None:
            style = ttk.Style(self._root().style.theme_use())

        default_font = style.lookup("TEntry", "font")
        if default_font == '':
            default_font = self.cget("font")
        if default_font == '':
            default_font = nametofont("TkDefaultFont")

        # print(f"Default font: {default_font}")
        return default_font


class App(tk.Tk):

    def __init__(self, title, theme):
        super().__init__()
        self.style = ttk.Style(theme)
        self.title(title)

        self.minsize(self.winfo_width(), self.winfo_height())
        x_cordinate = int((self.winfo_screenwidth() / 2) - (self.winfo_width() / 2))
        y_cordinate = int((self.winfo_screenheight() / 2) - (self.winfo_height() / 2))
        self.geometry("+{}+{}".format(x_cordinate, y_cordinate - 20))

        frame = ttk.Frame(self)
        frame.pack(fill="both", expand=True)

        # Make the app responsive
        for index in [0, 1, 2]:
            frame.columnconfigure(index=index, weight=1)
            frame.rowconfigure(index=index, weight=1)

        # Create value lists
        self.option_menu_list = ["", "OptionMenu", "Option 1", "Option 2"]
        self.combo_list = ["Combobox", "Editable item 1", "Editable item 2"]
        self.readonly_combo_list = ["Readonly combobox", "Item 1", "Item 2"]

        # Create control variables
        self.var_0 = tk.BooleanVar()
        self.var_1 = tk.BooleanVar(value=True)
        self.var_2 = tk.BooleanVar()
        self.var_3 = tk.IntVar(value=2)
        self.var_4 = tk.StringVar(value=self.option_menu_list[1])
        self.var_5 = tk.DoubleVar(value=75.0)

        # Create widgets :)
        self.setup_widgets(frame)

    def setup_widgets(self, container):
        # Create a Frame for the Checkbuttons
        check_frame = ttk.LabelFrame(container, text="Checkbuttons", padding=(20, 10))
        check_frame.grid(row=0, column=0, padx=(20, 10), pady=(20, 10), sticky="nsew")

        # Checkbuttons
        check_1 = ttk.Checkbutton(check_frame, text="Unchecked", variable=self.var_0)
        check_1.grid(row=0, column=0, padx=5, pady=10, sticky="nsew")

        check_2 = ttk.Checkbutton(check_frame, text="Checked", variable=self.var_1)
        check_2.grid(row=1, column=0, padx=5, pady=10, sticky="nsew")

        check_3 = ttk.Checkbutton(check_frame, text="Third state", variable=self.var_2)
        check_3.state(["alternate"])
        check_3.grid(row=2, column=0, padx=5, pady=10, sticky="nsew")

        check_4 = ttk.Checkbutton(check_frame, text="Disabled", state="disabled")
        check_4.state(["disabled !alternate"])
        check_4.grid(row=3, column=0, padx=5, pady=10, sticky="nsew")

        # Separator
        separator = ttk.Separator(container)
        separator.grid(row=1, column=0, padx=(20, 10), pady=10, sticky="ew")

        # Create a Frame for the Radiobuttons
        radio_frame = ttk.LabelFrame(container, text="Radiobuttons", padding=(20, 10))
        radio_frame.grid(row=2, column=0, padx=(20, 10), pady=10, sticky="nsew")

        # Radiobuttons
        radio_1 = ttk.Radiobutton(radio_frame, text="Unselected", variable=self.var_3, value=1)
        radio_1.grid(row=0, column=0, padx=5, pady=10, sticky="nsew")
        radio_2 = ttk.Radiobutton(radio_frame, text="Selected", variable=self.var_3, value=2)
        radio_2.grid(row=1, column=0, padx=5, pady=10, sticky="nsew")
        radio_4 = ttk.Radiobutton(radio_frame, text="Disabled", state="disabled")
        radio_4.grid(row=3, column=0, padx=5, pady=10, sticky="nsew")

        # Create a Frame for input widgets
        widgets_frame = ttk.Frame(container, padding=(0, 0, 0, 10))
        widgets_frame.grid(row=0, column=1, padx=10, pady=(30, 10), sticky="nsew", rowspan=3)
        widgets_frame.columnconfigure(index=0, weight=1)

        # Entry
        entry = ttk.Entry(widgets_frame)
        entry.insert(0, "Entry")
        entry.grid(row=0, column=0, padx=5, pady=(0, 10), sticky="ew")

        # Spinbox
        spinbox = ttk.Spinbox(widgets_frame, from_=0, to=100, increment=0.1)
        spinbox.insert(0, "Spinbox")
        spinbox.grid(row=1, column=0, padx=5, pady=10, sticky="ew")

        # Combobox
        combobox = ttk.Combobox(widgets_frame, values=self.combo_list)
        combobox.current(0)
        combobox.grid(row=2, column=0, padx=5, pady=10, sticky="ew")

        # Read-only combobox
        readonly_combo = ttk.Combobox(widgets_frame, state="readonly", values=self.readonly_combo_list)
        readonly_combo.current(0)
        readonly_combo.grid(row=3, column=0, padx=5, pady=10, sticky="ew")

        # Menu for the Menubutton
        menu = tk.Menu(self)
        menu.add_command(label="Menu item 1")
        menu.add_command(label="Menu item 2")
        menu.add_separator()
        menu.add_command(label="Menu item 3")
        menu.add_command(label="Menu item 4")

        # Menubutton
        menubutton = ttk.Menubutton(widgets_frame, text="Menubutton", menu=menu, direction="below")
        menubutton.grid(row=4, column=0, padx=5, pady=10, sticky="nsew")

        # OptionMenu
        optionmenu = ttk.OptionMenu(widgets_frame, self.var_4, *self.option_menu_list)
        optionmenu.grid(row=5, column=0, padx=5, pady=10, sticky="nsew")

        # Button
        button = ttk.Button(widgets_frame, text="Button")
        button.grid(row=6, column=0, padx=5, pady=10, sticky="nsew")

        # Accentbutton
        accentbutton = ttk.Button(widgets_frame, text="Accent button")
        accentbutton.grid(row=7, column=0, padx=5, pady=10, sticky="nsew")

        # Togglebutton
        togglebutton = ttk.Checkbutton(widgets_frame, text="Toggle button")
        togglebutton.grid(row=8, column=0, padx=5, pady=10, sticky="nsew")

        # Switch
        switch = ttk.Checkbutton(widgets_frame, text="Switch")
        switch.grid(row=9, column=0, padx=5, pady=10, sticky="nsew")

        # StyledText
        text = StyledText(widgets_frame, height=5, wrap="word", width=10)
        text.insert(tk.END, "This is the initial content of the StyledText widget.\n")
        text.grid(row=10, column=0, padx=5, pady=(0, 10), sticky="ew")

        # Panedwindow
        paned = ttk.PanedWindow(container)
        paned.grid(row=0, column=2, pady=(25, 5), sticky="nsew", rowspan=3)

        # Pane #1
        pane_1 = ttk.Frame(paned, padding=5)
        paned.add(pane_1, weight=1)

        # Scrollbar
        scrollbar = ttk.Scrollbar(pane_1)
        scrollbar.pack(side="right", fill="y")

        # Treeview
        treeview = ttk.Treeview(pane_1, selectmode="browse", yscrollcommand=scrollbar.set, columns=(1, 2), height=10,)
        treeview.pack(expand=True, fill="both")
        scrollbar.config(command=treeview.yview)

        # Treeview columns
        treeview.column("#0", anchor="w", width=120)
        treeview.column(1, anchor="w", width=120)
        treeview.column(2, anchor="w", width=120)

        # Treeview headings
        treeview.heading("#0", text="Column 1", anchor="center")
        treeview.heading(1, text="Column 2", anchor="center")
        treeview.heading(2, text="Column 3", anchor="center")

        # Define treeview data
        treeview_data = [
            ("", 1, "Parent", ("Item 1", "Value 1")), (1, 2, "Child", ("Subitem 1.1", "Value 1.1")), (1, 3, "Child", ("Subitem 1.2", "Value 1.2")),
            (1, 4, "Child", ("Subitem 1.3", "Value 1.3")), (1, 5, "Child", ("Subitem 1.4", "Value 1.4")), ("", 6, "Parent", ("Item 2", "Value 2")),
            (6, 7, "Child", ("Subitem 2.1", "Value 2.1")), (6, 8, "Sub-parent", ("Subitem 2.2", "Value 2.2")),
            (8, 9, "Child", ("Subitem 2.2.1", "Value 2.2.1")), (8, 10, "Child", ("Subitem 2.2.2", "Value 2.2.2")),
            (8, 11, "Child", ("Subitem 2.2.3", "Value 2.2.3")), (6, 12, "Child", ("Subitem 2.3", "Value 2.3")),
            (6, 13, "Child", ("Subitem 2.4", "Value 2.4")), ("", 14, "Parent", ("Item 3", "Value 3")),
            (14, 15, "Child", ("Subitem 3.1", "Value 3.1")), (14, 16, "Child", ("Subitem 3.2", "Value 3.2")),
            (14, 17, "Child", ("Subitem 3.3", "Value 3.3")), (14, 18, "Child", ("Subitem 3.4", "Value 3.4")),
            ("", 19, "Parent", ("Item 4", "Value 4")), (19, 20, "Child", ("Subitem 4.1", "Value 4.1")),
            (19, 21, "Sub-parent", ("Subitem 4.2", "Value 4.2")), (21, 22, "Child", ("Subitem 4.2.1", "Value 4.2.1")),
            (21, 23, "Child", ("Subitem 4.2.2", "Value 4.2.2")), (21, 24, "Child", ("Subitem 4.2.3", "Value 4.2.3")),
            (19, 25, "Child", ("Subitem 4.3", "Value 4.3")),
        ]

        # Insert treeview data
        for item in treeview_data:
            treeview.insert(parent=item[0], index="end", iid=item[1], text=item[2], values=item[3])
            if item[0] == "" or item[1] in {8, 21}:
                treeview.item(item[1], open=True)  # Open parents

        # Select and scroll
        treeview.selection_set(10)
        treeview.see(7)

        # Notebook, pane #2
        pane_2 = ttk.Frame(paned, padding=5)
        paned.add(pane_2, weight=3)

        # Notebook, pane #2
        notebook = ttk.Notebook(pane_2)
        notebook.pack(fill="both", expand=True)

        # Tab #1
        tab_1 = ttk.Frame(notebook)
        for index in [0, 1]:
            tab_1.columnconfigure(index=index, weight=1)
            tab_1.rowconfigure(index=index, weight=1)
        notebook.add(tab_1, text="Tab 1")

        # Scale
        scale = ttk.Scale(tab_1, from_=100, to=0, variable=self.var_5, command=lambda event: var_5.set(scale.get()),)
        scale.grid(row=0, column=0, padx=(20, 10), pady=(20, 0), sticky="ew")

        # Progressbar
        progress = ttk.Progressbar(tab_1, value=0, variable=self.var_5, mode="determinate")
        progress.grid(row=0, column=1, padx=(10, 20), pady=(20, 0), sticky="ew")

        # Label
        label = ttk.Label(tab_1, text="Ttk Widget Demo", justify="center", font=("-size", 15, "-weight", "bold"),)
        label.grid(row=1, column=0, pady=10, columnspan=2)

        # Tab #2
        tab_2 = ttk.Frame(notebook)
        notebook.add(tab_2, text="Tab 2")

        # Tab #3
        tab_3 = ttk.Frame(notebook)
        notebook.add(tab_3, text="Tab 3")

        # Create a Frame for the theme selection
        theme_frame = ttk.LabelFrame(container, text="Theme Selection", padding=(20, 10))
        theme_frame.grid(row=3, column=0, padx=(20, 10), pady=(20, 10), sticky="nsew")

        # Theme selection Combobox
        theme_combobox = ttk.Combobox(theme_frame, values=themes_list, state="readonly")
        theme_combobox.set("pulse")  # Set the initial theme
        theme_combobox.bind("<<ComboboxSelected>>", self.change_theme)  # Bind the event handler
        theme_combobox.pack(padx=10, pady=10)

        # Sizegrip
        sizegrip = ttk.Sizegrip(container)
        sizegrip.grid(row=100, column=100, padx=(0, 5), pady=(0, 5))

    def change_theme(self, event=None):
        selected_theme = event.widget.get()
        self.style = ttk.Style(selected_theme)


if __name__ == "__main__":
    main = App(title='Test Theme', theme='pulse')
    main.mainloop()
