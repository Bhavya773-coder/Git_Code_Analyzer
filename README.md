Git Code Analyzer

Git Code Analyzer is a Python-based tool designed to analyze GitHub repositories and provide concise summaries of their codebases. It leverages GitHub's API to fetch repository data and employs language models to generate human-readable summaries, aiding developers in quickly understanding the structure and content of a repository.

Features

Repository Scraping: Fetches repository metadata, file structures, and commit histories.
Commit Analysis: Processes commit data to extract meaningful insights.
LLM Summarization: Utilizes language models to generate summaries of the repository's codebase.
Installation

Clone the Repository:
git clone https://github.com/Bhavya773-coder/Git_Code_Analyzer.git
cd Git_Code_Analyzer
Create a Virtual Environment (Optional but recommended):
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
Install Dependencies:
pip install -r requirements.txt
Usage

Run the Application:
python app.py
Follow the Prompts:
The application will prompt you to enter the URL of the GitHub repository you wish to analyze.
View the Summary:
After processing, the tool will output a summary of the repository's codebase.
Project Structure

├── app.py               # Main application script

├── scrapper.py          # Module for scraping repository data

├── llm_summarizer.py    # Module for generating summaries using LLMs

├── requirements.txt     # List of Python dependencies

└── .gitignore           # Specifies files to ignore in version control
Dependencies

Ensure that the following Python packages are installed (as specified in requirements.txt):

requests
openai
PyGithub
Any other dependencies listed in the requirements.txt file.
Contributing

Contributions are welcome! If you'd like to enhance the functionality or fix issues, please fork the repository and submit a pull request.
