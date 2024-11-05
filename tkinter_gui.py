from tkinter import Tk
from tkinter import ttk
from itertools import product

if __name__ == "__main__":
    root = Tk()
    frm = ttk.Frame(root, padding=10)
    frm.grid()
    ttk.Label(root, text="Hello")
    for x, y in product(range(9), range(9)):
        ttk.Button(frm, width=5, text=" ", command=root.destroy).grid(column=x, row=y)
    root.mainloop()
