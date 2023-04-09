import openai
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import requests
import logging
import pyperclip
import base64
import configparser

logging.basicConfig(level=logging.INFO)

def get_default_branch(repo_owner, repo_name, personal_access_token):
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}"
    headers = {'Authorization': f'token {personal_access_token}'}
    response = requests.get(url, headers=headers)
    response_data = response.json()

    if response.status_code != 200:
        raise Exception(response_data['message'])

    logging.info(f"Default branch for repo {repo_owner}/{repo_name}: {response_data['default_branch']}")
    return response_data['default_branch']

def get_repo_files(repo_owner, repo_name, personal_access_token):
    try:
        default_branch = get_default_branch(repo_owner, repo_name, personal_access_token)
    except Exception as e:
        raise Exception(f"Error fetching default branch: {str(e)}")

    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/git/trees/{default_branch}?recursive=1"
    headers = {'Authorization': f'token {personal_access_token}'}
    response = requests.get(url, headers=headers)
    response_data = response.json()

    if response.status_code != 200:
        if 'message' in response_data and response_data['message'] == 'Not Found':
            raise Exception("Repository not found or incorrect personal access token.")
        else:
            raise Exception(response_data['message'])

    tree = response_data['tree']
    for file in tree:
        if file["type"] == "blob":
            file_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{file['path']}"
            file_url_response = requests.get(file_url, headers=headers)
            file_url_data = file_url_response.json()
            if file_url_response.status_code == 200:
                file["content"] = file_url_data.get("content", None)
            else:
                file["content"] = None
        else:
            file["content"] = None

    logging.info(f"Number of files in the repo {repo_owner}/{repo_name}: {len(tree)}")
    for file in tree:
        logging.info(f"File: {file['path']}, Type: {file['type']}, Content: {file['content']}")
    return tree

                 
def download_file_content(file_url, personal_access_token):
    headers = {'Authorization': f'token {personal_access_token}'}
    response = requests.get(file_url, headers=headers)
    return response.text

def download_and_process_file(file, token):
    if not file["download_url"]:
        return None
    file_content = download_file_content(file["download_url"], token)
    logging.info(f"File path: {file['path']}, download URL: {file['download_url']}")
    return f"\n\n====== {file['path']} ===\n\n{file_content}"

def ask_question(files, question, prompt, status_var, token):
    status_var.set('Asking the question...')
    code_text = "\n\n".join([base64.b64decode(file["content"]).decode('utf-8') for file in files if file["type"] == "blob" and file["path"].endswith(('.py', '.js', '.java', '.cpp', '.c', '.cs', '.rb')) and file["content"]])
    logging.info("Code Text: \n" + code_text)
    max_text_tokens = 4000 - len(question) - 20  # Adjusting the text length to fit within the model's token limit
    logging.info("Prompt: " + prompt)
    prompt = prompt.format(text=code_text[:max_text_tokens], question=question)
    logging.info("Formatted prompt: " + prompt)
    response = openai.Completion.create(
        model="text-davinci-003",
        prompt=prompt,
        temperature=0.9,
        max_tokens=1000,
        top_p=0.9,
        frequency_penalty=0.0,
        presence_penalty=0.0
       )
    answer = response.choices[0].text.strip()
    logging.info("Answer: " + answer)
    status_var.set('Answer generated')
    return answer


def load_config():
    config = configparser.ConfigParser()
    if os.path.exists('config.ini'):
        config.read('config.ini')
        return config
    else:
        return None

def save_config(api_key):
    config = configparser.ConfigParser()
    config['DEFAULT'] = {'api_key': api_key}
    with open('config.ini', 'w') as configfile:
        config.write(configfile)

def generate_report():
    try:
        repo_url = url_entry.get()
        if not repo_url:
            messagebox.showerror(title='Error', message='Please enter a GitHub repository URL.')
            return

        api_key = api_key_entry.get()
        if not api_key:
            messagebox.showerror(title='Error', message='Please enter your OpenAI API key.')
            return
        openai.api_key = api_key
        save_config(api_key)  # Save the API key to the config file           
                 
        repo_parts = repo_url.split("/")
        if len(repo_parts) < 5:
            messagebox.showerror(title='Error', message='Invalid GitHub repository URL.')
            return

        repo_owner, repo_name = repo_parts[-2], repo_parts[-1]

        token = token_entry.get()  # Add this line to define the token variable
        if not token:
            messagebox.showerror(title='Error', message='Please enter your GitHub Personal Access Token.')
            return

        files = get_repo_files(repo_owner, repo_name, token)

        question = question_entry.get()
        prompt = prompt_entry.get()
        answer = ask_question(files, question, prompt, status_var, token)

        output_text.delete(1.0, tk.END)
        output_text.insert(tk.END, answer)

    except Exception as e:
        messagebox.showerror(title='Error', message=str(e))
        pyperclip.copy(str(e))




root = tk.Tk()
root.title('GitHub Repo Report Generator')

tab_control = ttk.Notebook(root)
tab1 = ttk.Frame(tab_control)
tab2 = ttk.Frame(tab_control)
tab_control.add(tab1, text='Report')
tab_control.add(tab2, text='Ask Question')
tab_control.pack(expand=1, fill='both')

url_label = tk.Label(tab1, text='GitHub Repository URL:')
url_label.pack(pady=10)

url_entry = tk.Entry(tab1, width=100)
url_entry.pack()

token_label = tk.Label(tab1, text='GitHub Personal Access Token:')
token_label.pack(pady=10)

token_entry = tk.Entry(tab1, width=100, show='*')
token_entry.pack()

generate_button = tk.Button(tab1, text='Generate Report', command=generate_report)
generate_button.pack(pady=10)

question_label = tk.Label(tab1, text='Question:')
question_label.pack(pady=10)

question_entry = tk.Entry(tab1, width=100)
question_entry.pack()

output_label = tk.Label(tab1, text='Answer:')
output_label.pack(pady=10)

output_text = tk.Text(tab1, height=20)
output_text.pack()

prompt_label = tk.Label(tab2, text='Prompt:')
prompt_label.pack(pady=10)

prompt = (
    "You are a world-class full-stack developer who has a broad set of technology skills at a high level. "
    "Based on the information in this codebase:\n\n"
    "{text}\n\n"
    "Answer the following question: {question}. Your response must be no more than 1000 tokens."
)

prompt_var = tk.StringVar()
prompt_var.set(prompt)
prompt_entry = tk.Entry(tab2, textvariable=prompt_var, width=100)
prompt_entry.pack()

status_var = tk.StringVar()
status_var.set('')
status_label = tk.Label(tab1, textvariable=status_var)
status_label.pack(pady=10)
                 
api_key_label = tk.Label(tab1, text='OpenAI API Key:')
api_key_label.pack(pady=10)

api_key_entry = tk.Entry(tab1, width=100, show='*')
api_key_entry.pack()                 

root.mainloop()

config = load_config()
if config:
    api_key_entry.insert(0, config['DEFAULT']['api_key'])
