## Setup: Install and Setup VS Code and Python
*   Install VS Code [here](https://https://code.visualstudio.com/docs/setup/setup-overview)
*   Be sure to setup a folder for you open through VS Code that will house all your future dev projects and python imports. Going forward we will call this the base dev folder.
*   Within VS Code install the [python extension](https://marketplace.visualstudio.com/items?itemName=ms-python.python)

Steps to install virtual enviroment 
*  In VS Code open command prompt by pressing SHIFT + COMMAND/ CTRL + P
*  Type in and select "Python: Create Environment"
*  Select a "Venv" enviroment

## Create test.py file and test python
*   In the same folder make a new folder called "Test" using the folder explorer on vs-code (top left folder icon)
*   In that folder make a file called "test.py"
*   In that file paste ```print("hell yeah I made a python file and ran it!")```
*   In the upper right corner press on the little play button to run the python.
*   In your vs-code terminal you should see text!

## Setup: Install Open AI library and run test
*  In VS Code open command prompt by pressing SHIFT + COMMAND/ CTRL + P
*  paste in ```pip install openai```
*  Go back to the test.py file 
*  Paste over everything with this code (change to your open ai key):
```python
import openai
import time

key_1 = '[YOUR OPEN AI KEY]'
prompt = 'What are three nicknames comma separated for a really great guy named Dan?'

def gpt_call(prompt, key):
    openai.api_key = key
    completion = openai.chat.completions.create(
        model='gpt-4o',
        messages=[
            {
                'role': 'user',
                'content': f'{prompt}',
            },
        ],
    )
    response = completion.choices[0].message.content
    time.sleep(1)
    return response

print(gpt_call(prompt, key_1))
```

*  Run (with play button upper right) and you should see a prompt back as a print from chat gpt!

## Setup: Installing and using PostgreSQL
*  You have to install PostgreSQL infrastructure on system first. [This link](https://www.prisma.io/dataguide/postgresql/setting-up-a-local-postgresql-database#setting-up-postgresql-on-macos) has best setup instructions, just [install via Mac here](https://www.postgresql.org/download/macosx/).
*  You should have the same psql database name and specs as mine so you don't have to change my code everytime:
  *  database='postgres' (database name)
  *  host='localhost'
  *  user='postgres'
  *  password='[password of your choice]' 
  *  port='5432'
*  Install [this extension](https://marketplace.visualstudio.com/items?itemName=ckolkman.vscode-postgres) in VSCode. The [default extension described in this article](https://www.commandprompt.com/education/how-to-connect-to-postgresql-from-visual-studio-code/) no longer works. 
*  Generally speaking any table you make within this database is for your computer only so you have a lot of liberty to mess up haha.