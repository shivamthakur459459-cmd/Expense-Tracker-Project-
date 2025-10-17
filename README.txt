Simple Expense Tracker - README

Files included:
- app.py                : Streamlit app source code
- requirements.txt      : Python packages to install (pip install -r requirements.txt)
- expenses_sample1.csv  : Sample data (CSV)
- expenses_sample2.csv  : Sample data (CSV)
- expenses_sample3.csv  : Sample data (CSV)

How to run (Windows / Linux / Mac):
1) Open terminal / command prompt.
2) Navigate to the folder containing these files.
   Example: cd path/to/expense_tracker
3) (Optional but recommended) Create and activate a virtual environment:
   python -m venv venv
   Windows: venv\Scripts\activate
   Linux/Mac: source venv/bin/activate
4) Install requirements:
   pip install -r requirements.txt
5) Run the app:
   streamlit run app.py
6) Browser will open the app. Use the form to add expenses or upload sample CSVs.

Notes:
- The app saves data to 'expenses.csv' in the same folder when you add expenses.
- If you want the app to start with sample data, upload one of the sample CSV files via the sidebar upload control.
- If you face any issues, tell me — I'll help fix them step-by-step.

Enjoy! — ChatGPT
