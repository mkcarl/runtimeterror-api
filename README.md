# Backend API server for Runtime Terror Inventory Management System
This is the **reimplementation** of the project for Dell Hack2Hire hackathon. The original project can be found [here](https://github.com/mkcarl/runtimeterror-original). 

In the original project, Django was used to build the backend of the project. 
However, due to the simple nature of this project, I had took the liberty to change 
to using Flask framework. 

# Project structure 
This backend consist of 2 parts, namely the API server and the email receiver script. 
The API server is built using Flask framework and the email receiver script is built using
the gmail API. 

Note: the keys required for Firebase and Gmail API is removed from this repository.

# Getting Started
## Installation 
1. Clone the repository
2. Create a virtual environment as to not pollute your global environment
    ```bash
    python -m venv venv 
    .\venv\Script\activate # for windows
    ```
3. Install the dependencies
    ```bash
    pip install -r requirements.txt
    ```
## Running the server
1. Run the server
    ```bash
    python app.py
    ```
1. Run the email receiver script
    ```bash
    python jobs/email_receiver.py
    ```

As per the last update of this project, the API server is hosted on Render.com, while the 
email receiver script is hosted on my personal EC2 instance. 