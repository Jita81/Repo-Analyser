import tkinter as tk
from tkinter import filedialog
from llama_index import GPTSimpleVectorIndex, SimpleDirectoryReader
import os

os.environ['OPENAI_API_KEY'] = 'api key'

class MyApp(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.master.configure(bg='#f0f0f0')
        self.pack(fill='both', expand=True)
        self.create_widgets()
        
    def create_widgets(self):
        self.select_dir_button = tk.Button(self, text="Select Directory", command=self.select_directory, bg='#0c7cd5', fg='white', activebackground='#0a5ca1', activeforeground='white', borderwidth=0, padx=10, pady=5)
        self.select_dir_button.pack(pady=(10,0))
        
        self.query_label = tk.Label(self, text="Query:", bg='#f0f0f0')
        self.query_label.pack()
        
        self.query_entry = tk.Entry(self)
        self.query_entry.pack(pady=(0,10), ipady=5, ipadx=10)
        
        self.search_button = tk.Button(self, text="Search", command=self.search, bg='#0c7cd5', fg='white', activebackground='#0a5ca1', activeforeground='white', borderwidth=0, padx=10, pady=5)
        self.search_button.pack(pady=(0,10))
        
        self.results_text = tk.Text(self, height=10, bg='white', fg='#333333', font=('Arial', 12), padx=10, pady=10)
        self.results_text.pack(fill='both', expand=True, padx=10)
        
def select_directory(self):
    directory = filedialog.askdirectory()
    if directory:
        self.directory = directory

        
    def search(self):
        try:
            documents = SimpleDirectoryReader(self.directory).load_data()
        except AttributeError:
            self.results_text.delete('1.0', tk.END)
            self.results_text.insert(tk.END, "Please select a directory first.")
            return
        
        index = GPTSimpleVectorIndex(documents)
        index.save_to_disk('index.json')
       
        # load from disk
        index = GPTSimpleVectorIndex.load_from_disk('index.json')
        
        query = self.query_entry.get()
        response = index.query(query)
        self.results_text.delete('1.0', tk.END)
        self.results_text.insert(tk.END, response)
        
root = tk.Tk()
root.title("Document Chatbot")
root.geometry("500x500")
app = MyApp(root)
app.mainloop()
