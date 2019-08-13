from tkinter import *
from tkinter import ttk
from tkinter import filedialog
from transform import transform
from PIL import ImageTk, Image
import logging

logging.basicConfig(format='[%(asctime)s] %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p',
                    filename='logs/mzTransformer.log', level=logging.INFO)


def search_file(*args):
    file_name = filedialog.askopenfilename()
    import_file.set(file_name)


def choose_result_directory(*args):
    result_directory.set(filedialog.askdirectory())


def transform_file(*args):
    if import_file.get() and result_directory.get() and result_filename.get():
        messages.set(transform(import_file.get(), result_directory.get(), result_filename.get()))
    else:
        messages.set("Please complete all the fields before transforming!!!")


root = Tk()
root.title("MZ Transformer")

mainframe = ttk.Frame(root, padding="3 3 12 12")
mainframe.grid(column=0, row=0, sticky=(N, W, E, S))
root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=1)

mz_logo = ImageTk.PhotoImage(Image.open("statics/mz_logo.png"))
import_file = StringVar()
result_directory = StringVar()
result_filename = StringVar()
messages = StringVar()

result_filename_entry = ttk.Entry(mainframe, width=20, textvariable=result_filename)

ttk.Label(mainframe, image=mz_logo).grid(column=1, columnspan=3, row=1)

ttk.Label(mainframe, text="ENACOM Export File:").grid(column=1, row=2, sticky=E)
ttk.Label(mainframe, textvariable=import_file, width=100).grid(column=2, row=2, sticky=(W, E))
ttk.Button(mainframe, text="Search File", command=search_file, width=20).grid(column=3, row=2, sticky=W)

ttk.Label(mainframe, text="Result Directory:").grid(column=1, row=3, sticky=E)
ttk.Label(mainframe, textvariable=result_directory, width=100).grid(column=2, row=3, sticky=(W, E))
ttk.Button(mainframe, text="Search Directory", command=choose_result_directory, width=20).grid(column=3, row=3,
                                                                                               sticky=W)

ttk.Label(mainframe, text="Result Filename:").grid(column=1, row=4, sticky=E)
result_filename_entry.grid(column=2, row=4, sticky=(W, E))

ttk.Button(mainframe, text="Transform", command=transform_file, width=140).grid(column=1, columnspan=3, row=5)

ttk.Label(mainframe, textvariable=messages).grid(column=1, columnspan=3, row=6, sticky=(W, E))

for child in mainframe.winfo_children(): child.grid_configure(padx=5, pady=5)

root.bind('<Return>', transform_file)

root.mainloop()
