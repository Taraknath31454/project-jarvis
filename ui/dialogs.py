"""Searchable help, notes, and safe file-result views."""
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from commands.catalog import CATEGORIES, search_commands
from ui.theme import BG, PANEL, CYAN, TEXT, MUTED, label, button, text_box, set_text

def command_palette(desktop, help_mode=False):
    window = tk.Toplevel(desktop.root)
    window.title('JARVIS • Command discovery' if help_mode else 'JARVIS • Command palette')
    window.geometry('690x490')
    window.configure(bg=BG)
    label(window, 'COMMAND DISCOVERY' if help_mode else 'COMMAND PALETTE', 14, CYAN).pack(anchor='w', padx=20, pady=(18, 8))
    category = tk.StringVar(value='All')
    combo = ttk.Combobox(window, textvariable=category, values=['All', *CATEGORIES], state='readonly')
    combo.pack(fill='x', padx=20, pady=5)
    query = tk.StringVar()
    label(window, 'Search commands…', 9, MUTED).pack(anchor='w', padx=20, pady=(7, 0))
    entry = tk.Entry(window, textvariable=query, bg=PANEL, fg=TEXT, insertbackground=CYAN, relief='flat', font=('Consolas', 13))
    entry.pack(fill='x', padx=20, pady=8, ipady=8)
    choices = tk.Listbox(window, bg=PANEL, fg=TEXT, selectbackground='#174153', relief='flat', bd=0,
                         font=('Segoe UI', 11), activestyle='none')
    choices.pack(fill='both', expand=True, padx=20)
    def filter_commands(*_):
        choices.delete(0, 'end')
        for item in search_commands(query.get(), category.get()): choices.insert('end', item)
        if choices.size(): choices.selection_set(0)
    def run(_=None):
        if choices.curselection():
            command = choices.get(choices.curselection()[0])
            window.destroy()
            desktop.submit(command)
    query.trace_add('write', filter_commands)
    combo.bind('<<ComboboxSelected>>', filter_commands)
    choices.bind('<Double-Button-1>', run)
    choices.bind('<Return>', run)
    entry.bind('<Return>', run)
    window.bind('<Escape>', lambda _: window.destroy())
    button(window, 'RUN SELECTED COMMAND  ↵', run, True).pack(anchor='e', padx=20, pady=15)
    filter_commands()
    entry.focus_set()
    return window

def notes_window(desktop):
    def display(rows):
        window = tk.Toplevel(desktop.root)
        window.title('JARVIS • Local notes')
        window.geometry('700x480')
        window.configure(bg=BG)
        label(window, 'LOCAL NOTES', 14, CYAN).pack(anchor='w', padx=20, pady=16)
        text = text_box(window, width=40)
        text.pack(fill='both', expand=True, padx=20)
        set_text(text, '\n\n'.join(f'{created[:16].replace("T", " ")}\n{note}' for _, created, note in rows) or 'No notes yet.')
        button(window, 'NEW NOTE', lambda: (window.destroy(), desktop.new_note()), True).pack(anchor='e', padx=20, pady=14)
    desktop.background(desktop.assistant.storage.notes, display)

def file_results(desktop, paths):
    window = tk.Toplevel(desktop.root)
    window.title('JARVIS • File finder')
    window.geometry('850x430')
    window.configure(bg=BG)
    label(window, 'FILE FINDER', 14, CYAN).pack(anchor='w', padx=20, pady=(16, 4))
    label(window, 'Select a result. Open allows folders, PDF, text and images; other types can be revealed safely.', 9, MUTED).pack(anchor='w', padx=20, pady=(0, 10))
    tree = ttk.Treeview(window, columns=('name', 'path', 'type'), show='headings', selectmode='browse')
    for key, caption, width in [('name', 'NAME', 200), ('path', 'PATH', 440), ('type', 'TYPE', 90)]:
        tree.heading(key, text=caption)
        tree.column(key, width=width, minwidth=60)
    tree.pack(fill='both', expand=True, padx=20)
    for i, value in enumerate(paths):
        path = Path(value)
        tree.insert('', 'end', iid=str(i+1), values=(path.name, value, path.suffix.upper() or 'Folder'))
    def act(open_file):
        if not tree.selection(): return
        # Resolve against this snapshot rather than a later search's mutable results.
        path = paths[int(tree.selection()[0])-1]
        current = desktop.assistant.files.results
        if path not in current:
            desktop.notify('Search results changed. Run the search again before opening this result.')
            return
        index = current.index(path)+1
        desktop.submit(f'open file result {index}' if open_file else f'open result {index}')
    buttons = tk.Frame(window, bg=BG)
    buttons.pack(fill='x', padx=20, pady=14)
    button(buttons, 'OPEN', lambda: act(True), True).pack(side='right')
    button(buttons, 'OPEN LOCATION', lambda: act(False)).pack(side='right', padx=10)
    return window
