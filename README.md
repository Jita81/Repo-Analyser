# Repo-Analyser
A basic analyser for github repos that allows you to question the whole repo.

**This currently takes about ~7 minutes for an application i'm testing it against to run. **

This is a simple document search application built using the Tkinter library in Python. The application uses the OpenAI GPT-3 language model to index a directory of documents and provides a search interface for querying the indexed documents.

Prerequisites
This code requires the following Python modules to be installed:

tkinter
llama_index
os
You also need to have an OpenAI API key to use this application. Set the OPENAI_API_KEY environment variable to your API key.

Usage
To use the application, run the script in a Python environment. A GUI window will appear with the following options:

"Select Directory" button: Click this button to choose a directory to index.
"Query" label and text entry: Enter a query term to search the indexed documents.
"Search" button: Click this button to perform a search.
"Results" text area: Displays the search results.
Once you have selected a directory and performed a search, the application will index the documents and save the index to a file called "index.json" in the current working directory. The index is then loaded from the file and used to perform the search. The search results are displayed in the "Results" text area.

Note: The first time you run the application, it may take some time to index the documents depending on the size of the directory.

License
This code is released under the MIT License.
