# Standard library imports
import functools
import os
import json
import hashlib
import difflib
import traceback
import sys
import threading
from pathlib import Path
from datetime import date
from threading import Thread
import subprocess

# Third-party imports
from flask import Flask, request, jsonify, send_from_directory, Response, render_template
from werkzeug.utils import safe_join
from flask_cors import CORS
from git import Repo, InvalidGitRepositoryError, NoSuchPathError, GitCommandError

# Local application imports
from papertlab.main import main as cli_main
from papertlab.agents import Coder
from papertlab.agents.base_coder import DB_PATH
from papertlab import models
from papertlab.io import InputOutput
from papertlab.commands import SwitchCoder
from papertlab.utils import extract_updated_code, execute_command, get_available_models
from papertlab.sql_utils import get_auto_commit_db_status, save_auto_commit_db, get_usage_data_db, get_monthly_usage_db, get_latest_usage_db, store_project_usage_db
from papertlab.models import DEFAULT_MODEL_NAME

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Add a global variable to store the current model
current_model = None

# Global variable to store the last known file structure hash
last_file_structure_hash = None

initialization_complete = False
initialization_thread = None

coder = None
coder_lock = threading.Lock()

class Logger:
    def __init__(self):
        self.logs = []
        self.capture = False
        self.lock = threading.Lock()

    def write(self, message):
        with self.lock:
            if "POST /api/chat HTTP/1.1" in message:
                self.capture = True
            if self.capture:
                self.logs.append(message.strip())
            sys.__stdout__.write(message)  # Use sys.__stdout__ to avoid recursion

    def flush(self):
        sys.__stdout__.flush()

    def get_logs(self):
        with self.lock:
            logs = self.logs
            self.logs = []
            self.capture = False
            return logs

logger = Logger()
sys.stdout = logger
sys.stderr = logger

print("papertlab GUI started. Initializing...")

def handle_recursion_error(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except RecursionError:
            error_message = "RecursionError: maximum recursion depth exceeded"
            print(error_message, file=sys.__stderr__)
            return jsonify({"error": error_message}), 500
    return wrapper

# API endpoint to get the current API keys
@app.route('/api/get_api_keys', methods=['GET'])
def get_api_keys():
    return jsonify({
        'openai_api_key': os.getenv('OPENAI_API_KEY', ''),
        'anthropic_api_key': os.getenv('ANTHROPIC_API_KEY', ''),
        'gemini_api_key': os.getenv('GEMINI_API_KEY', ''),
        'groq_api_key': os.getenv('GROQ_API_KEY', ''),
        'ollama_api_base': os.getenv('OLLAMA_API_BASE', ''),
        'cohere_api_key': os.getenv('COHERE_API_KEY', '')
    })

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def index(path):
    return send_from_directory(app.template_folder, 'index.html')

@app.route('/settings')
def serve_settings():
    return render_template('settings.html')

@app.route('/api/check_api_key', methods=['GET'])
def check_api_key():
    openai_key_present = 'OPENAI_API_KEY' in os.environ
    anthropic_key_present = 'ANTHROPIC_API_KEY' in os.environ

    if openai_key_present or anthropic_key_present:
        return jsonify({
            "openai_key_present": openai_key_present,
            "anthropic_key_present": anthropic_key_present
        })
    else:
        return jsonify({
            "openai_key_present": False,
            "anthropic_key_present": False
        })

    
def get_uncommitted_files():
    try:
        # Get list of untracked files
        untracked_files = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard']).decode().splitlines()
        
        # Get list of modified files
        modified_files = subprocess.check_output(['git', 'diff', '--name-only']).decode().splitlines()
        
        # Get list of staged files
        staged_files = subprocess.check_output(['git', 'diff', '--staged', '--name-only']).decode().splitlines()
        
        uncommitted_files = list(set(untracked_files + modified_files + staged_files))
        
        if uncommitted_files:
            print(f"Uncommitted files found: {uncommitted_files}")
        else:
            print("No uncommitted files found.")
        
        return uncommitted_files
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while checking for uncommitted files: {e}")
        return []


def initialize_coder():
    global coder, current_model, initialization_complete
    try:
        # Try to initialize Git repo
        try:
            repo = Repo(os.getcwd())
        except (InvalidGitRepositoryError, NoSuchPathError):
            # If it's not a Git repo, initialize one
            try:
                repo = Repo.init(os.getcwd())
                print("Initialized new Git repository")
            except Exception as e:
                print(f"Failed to initialize Git repository: {str(e)}")
                return jsonify({"error": f"Failed to initialize Git repository: {str(e)}"}), 500

        # Get uncommitted files before initializing
        uncommitted_files = get_uncommitted_files()
        print("uncommitted_files==================", uncommitted_files)

        coder = cli_main(return_coder=True)

        # Check auto_commit setting from the database
        auto_commit_setting = get_auto_commit_db_status(DB_PATH)

        if auto_commit_setting:
            if uncommitted_files and uncommitted_files != []:
                coder.auto_commit(set(uncommitted_files))

        if not isinstance(coder, Coder):
            raise ValueError("Failed to initialize Coder")
        # Use the current_model if it's set, otherwise use DEFAULT_MODEL
        model_to_use = current_model or get_available_models()[0] if len(get_available_models()) >= 1 else DEFAULT_MODEL_NAME
        coder.main_model = models.Model(model_to_use)
        print("Coder initialized successfully")
    except Exception as e:
        print(f"Error initializing Coder: {str(e)}")
        return jsonify({"error": f"Failed to initialize Coder: {str(e)}"}), 500
    finally:
        initialization_complete = True
        
@handle_recursion_error
@app.route('/api/init', methods=['POST'])
def initialize():
    global initialization_thread
    if initialization_thread is None or not initialization_thread.is_alive():
        initialization_thread = Thread(target=initialize_coder)
        initialization_thread.start()
    return jsonify({"message": "Initialization started"}), 202

@app.route('/api/initialization_status', methods=['GET'])
def get_initialization_status():
    global initialization_complete, coder, current_model
    if initialization_complete and coder:
        current_model = current_model or coder.main_model.name
    return jsonify({
        "complete": initialization_complete,
        "announcements": coder.get_announcements() if initialization_complete else [],
        "files": get_file_structure(coder.get_all_relative_files()) if initialization_complete else {},
        "initial_chat_files": coder.get_inchat_relative_files() if initialization_complete else [],
        "models": get_available_models(),
        "current_model": current_model or get_available_models()[0] if len(get_available_models()) >= 1 else DEFAULT_MODEL_NAME
    })

# Modify your existing routes to check for initialization
def check_initialization(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if not initialization_complete:
            return jsonify({"error": "Initialization not complete"}), 503
        return func(*args, **kwargs)
    return wrapper

@app.route('/api/save_auto_commit', methods=['POST'])
def save_auto_commit():
    data = request.json
    auto_commit = data.get('auto_commit')

    print("auto_commit===========================", auto_commit) 

    status = save_auto_commit_db(DB_PATH, auto_commit)

    return jsonify({"success": status})


@app.route('/api/get_auto_commit_status', methods=['GET'])
def get_auto_commit_status():
    auto_commit_status = get_auto_commit_db_status(DB_PATH)
    return jsonify({"auto_commit": auto_commit_status})

@handle_recursion_error
@app.route('/api/usage', methods=['GET'])
def get_usage():
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    offset = (page - 1) * per_page

    total_count, results = get_usage_data_db(DB_PATH, per_page, offset)
    
    usage_data = [
        {
            "id": row[0],
            "project_id": row[1],
            "model": row[2],
            "input_token": row[3],
            "output_token": row[4],
            "cost": row[5],
            "total_cost": row[6],
            "datetime": row[7]
        }
        for row in results
    ]
    
    return jsonify({
        "usage": usage_data,
        "total": total_count
    })

@app.route('/api/monthly_usage', methods=['GET'])
def get_monthly_usage():
    try:
        # Get the first day of the current month
        first_day_of_month = date.today().replace(day=1).isoformat()

        result = get_monthly_usage_db(DB_PATH, first_day_of_month)
        
        total_tokens = int(result[0] or 0)
        total_cost = float(result[1] or 0)
        
        return jsonify({
            "total_tokens": total_tokens,
            "total_cost": total_cost
        })
    except Exception as e:
        print(f"Error in get_monthly_usage: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

def update_current_model(model_name):
    global current_model
    current_model = model_name

@app.route('/api/set_model', methods=['PUT'])
def set_model():
    global coder, current_model
    data = request.json
    new_model = data.get('model')
    
    if not new_model:
        return jsonify({"error": "No model specified"}), 400

    with coder_lock:
        if coder is None:
            return jsonify({"error": "Coder not initialized"}), 500

        try:
            update_current_model(new_model)
            coder.main_model = models.Model(new_model)
            # Create a new coder instance with the new model
            # new_coder = cli_main(return_coder=True)
            # new_coder.main_model = models.Model(new_model)
            
            # # Copy over relevant state from the old coder
            # new_coder.abs_fnames = coder.abs_fnames
            # new_coder.cur_messages = coder.cur_messages
            # new_coder.done_messages = coder.done_messages
            
            # # Replace the old coder with the new one
            # coder = new_coder

            # current_model = new_model  
            
            # Get updated announcements and files
            announcements = coder.get_announcements()
            files = get_file_structure(coder.get_all_relative_files())
            
            return jsonify({
                "success": True,
                "message": f"Model set to {new_model}",
                "current_model": current_model,
                "announcements": announcements,
                "files": files or {}  # Ensure files is always an object
            })
        except Exception as e:
            return jsonify({"error": f"Failed to set model: {str(e)}"}), 500
        
def get_latest_usage():

    result = get_latest_usage_db(DB_PATH)

    return {
        'total_tokens': result[0] or 0,
        'total_cost': result[1] or 0
    }

def apply_changes_to_file(filename, search, replace):
    """
    Apply the changes to the specified file.
    
    :param filename: The name of the file to modify
    :param search: The original code block
    :param replace: The modified code block
    """
    try:
        # Read the entire content of the file
        with open(filename, 'r', encoding='utf-8') as file:
            file_content = file.read()

        # Split the content into lines
        file_lines = file_content.splitlines()
        search_lines = search.splitlines()
        replace_lines = replace.splitlines()

        # Find the location of the search block in the file
        matcher = difflib.SequenceMatcher(None, file_content, search)
        match = matcher.find_longest_match(0, len(file_content), 0, len(search))

        if match.size == len(search):
            # If an exact match is found, replace it
            start_line = file_content.count('\n', 0, match.a)
            end_line = start_line + len(search_lines)
            
            new_content = (
                file_lines[:start_line] +
                replace_lines +
                file_lines[end_line:]
            )

            # Write the modified content back to the file
            with open(filename, 'w', encoding='utf-8') as file:
                file.write('\n'.join(new_content))

            print(f"Changes applied successfully to {filename}")
        else:
            print(f"Exact match not found in {filename}. Changes not applied.")

    except FileNotFoundError:
        print(f"File not found: {filename}")
    except PermissionError:
        print(f"Permission denied: Unable to modify {filename}")
    except Exception as e:
        print(f"An error occurred while modifying {filename}: {str(e)}")
        
@app.route('/api/chat', methods=['POST'])
@check_initialization
def chat():
    global coder, logger, current_model
    data = request.json
 
    with coder_lock:
        if coder is None:
            print("Error: Coder not initialized")
            return jsonify({"error": "Coder not initialized"}), 500

    model = data.get('model') or current_model or get_available_models()[0] if len(get_available_models()) >= 1 else DEFAULT_MODEL_NAME
    command = data.get('command', 'code')
    message = data.get('message', '')
    selected_code = data.get('selectedCode', '')
    file = data.get('file', '')
    print(f"Received {command} command: {message} (model: {model})")

    def generate():
        global coder 
        try:
            yield f"data: {json.dumps({'chunk': f'Processing {command} command\n'})}\n\n"

            try:
                if command == 'inline':
                    inline_coder = Coder.create(
                        main_model=coder.main_model,
                        io=coder.io,
                        edit_format="inline",
                        from_coder=coder
                    )
                    result, temp_coder = inline_coder.cmd_inline(f"{data['selectedCode']}\n{message}")
                    
                    # Extract the edits
                    edits = temp_coder.get_edits()
                    
                    if edits:
                        # Assuming we're only dealing with one edit at a time for inline changes
                        filename, search, replace = edits[0]
                        
                        # Check if we have a valid filename
                        if filename != "inline_edit.txt":
                            # Apply the changes to the file
                            # You'll need to implement a method to apply these changes to the file
                            apply_changes_to_file(filename, search, replace)
                        
                        # Send the result back to the client
                        yield f"data: {json.dumps({'updatedCode': replace})}\n\n"
                    else:
                        yield f"data: {json.dumps({'error': 'No valid edits found'})}\n\n"
                if command == 'code':
                    if selected_code:
                        message_with_code = f"In the file {file}, please modify this code:\n\n{selected_code}\n\nModification request: {message}"
                        result, temp_coder = coder.commands.cmd_code(message_with_code)
                    else:
                        result, temp_coder = coder.commands.cmd_code(message)
                elif command == 'ask':
                    result, temp_coder  = coder.commands.cmd_ask(message)
                elif command == 'autopilot':
                    autopilot_coder = Coder.create(
                        main_model=coder.main_model,
                        io=coder.io,
                        edit_format="autopilot",
                        from_coder=coder
                    )
                    result = autopilot_coder.run_autopilot(message)
                    temp_coder = autopilot_coder
                else:
                    yield f"data: {json.dumps({'chunk': f'Unknown command: {command}\n'})}\n\n"
                    return
                
            except SwitchCoder as sc:
                coder = Coder.create(**sc.kwargs)
                result = None
                
            if isinstance(result, SwitchCoder):
                coder = Coder.create(**result.kwargs)
 
            messages = temp_coder.partial_response_content

            yield f"data: {json.dumps({'chunk': f"{messages}\n"})}\n\n"
            
            project_name = os.path.basename(os.getcwd())
            # Update project usage in the database
            store_project_usage_db(DB_PATH, project_name, model, temp_coder)

            # Get and send updated usage information
            latest_usage = get_latest_usage()
            yield f"data: {json.dumps({'usage': latest_usage})}\n\n"

            # Send completion message
            completion_message = f"{command.capitalize()} command completed.\n"
            yield f"data: {json.dumps({'chunk': completion_message})}\n\n"

            # Update file structure after changes
            updated_files = get_file_structure(temp_coder.get_all_relative_files())
            yield f"data: {json.dumps({'updated_files': updated_files})}\n\n"

            if command == 'code' and temp_coder.git_commit_id and temp_coder.git_commit_id != '':
                commit_id = '\n\n' + temp_coder.git_commit_id + '\n\n'
                yield f"data: {json.dumps({'chunk': commit_id})}\n\n"

            if selected_code:
                # Extract the updated code from the result
                updated_code = extract_updated_code(result)
                yield f"data: {json.dumps({'updatedCode': updated_code})}\n\n"

        except Exception as e:
            error_message = f"An error occurred: {str(e)}\n{traceback.format_exc()}"
            print(f"Error: {error_message}")
            yield f"data: {json.dumps({'error': error_message, 'logs': logger.get_logs()})}\n\n"

    return Response(generate(), mimetype='text/event-stream')


@app.route('/api/execute_command', methods=['POST'])
def execute_command_route():
    global coder
    data = request.json
    command = data['command']
    
    if not coder:
        return jsonify({"error": "Coder not initialized"}), 500

    stdout, stderr = execute_command(command)
    
    if stdout:
        result = stdout.strip()
    elif stderr:
        result = f"Error: {stderr.strip()}"
    else:
        result = "Command executed successfully, but returned no output."
    
    return jsonify({"result": result})

@app.route('/api/logs', methods=['GET'])
def get_logs():
    global logger
    logs = logger.get_logs()
    return jsonify({"logs": logs})

@app.route('/api/file_content', methods=['GET'])
def get_file_content():
    global coder
    file_path = request.args.get('file')
    if not file_path:
        return jsonify({"error": "No file specified"}), 400

    try:
        # Use the current working directory as the root
        root_dir = os.getcwd()
        
        # Handle the special case for papertlab files
        if file_path.startswith('papertlab/') or file_path.startswith('papertlab\\'):
            root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Normalize the file path
        file_path = file_path.replace('\\', '/')
        
        # Use safe_join to prevent path traversal attacks
        safe_path = safe_join(root_dir, file_path)
        
        if safe_path is None or not os.path.exists(safe_path):
            return jsonify({"error": f"File not found: {file_path}"}), 404

        if os.path.getsize(safe_path) == 0:
            return jsonify({"content": ""})

        with open(safe_path, 'r', encoding='utf-8') as file:
            content = file.read()
        return jsonify({"content": content})
    except Exception as e:
        print(f"Error reading file: {str(e)}")
        return jsonify({"error": f"Error reading file: {str(e)}"}), 500

@app.route('/api/update_file', methods=['POST'])
def update_file():
    global coder
    data = request.json
    file_path = data.get('file')
    new_content = data.get('content')

    if not file_path or new_content is None:
        return jsonify({"error": "File path and content are required"}), 400

    try:
        # Use the current working directory as the root
        root_dir = os.getcwd()
        
        # Handle the special case for papertlab files
        if file_path.startswith('papertlab/') or file_path.startswith('papertlab\\'):
            root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Normalize the file path
        file_path = file_path.replace('\\', '/')
        
        # Use safe_join to prevent path traversal attacks
        safe_path = safe_join(root_dir, file_path)
        
        if safe_path is None or not os.path.exists(safe_path):
            return jsonify({"error": f"File not found: {file_path}"}), 404

        # Use the InputOutput class to write the file
        io = InputOutput()
        io.write_text(safe_path, new_content)

        return jsonify({"message": f"File {file_path} updated successfully"})
    except Exception as e:
        print(f"Error updating file: {str(e)}")
        return jsonify({"error": f"Error updating file: {str(e)}"}), 500

@app.route('/api/set_api_key', methods=['POST'])
def set_api_key():
    data = request.json
    api_keys = {
        'OPENAI_API_KEY': data.get('openai_key'),
        'ANTHROPIC_API_KEY': data.get('anthropic_key'),
        'GEMINI_API_KEY': data.get('gemini_key'),
        'GROQ_API_KEY': data.get('groq_key'),
        'OLLAMA_API_BASE': data.get('ollama_base'),
        'COHERE_API_KEY': data.get('cohere_key')
    }
    
    for key, value in api_keys.items():
        if value and value != '':
            os.environ[key] = value
    
    return jsonify({"success": True})

@app.route('/api/check_new_files', methods=['GET'])
def check_new_files():
    global last_file_structure_hash

    try:
        repo = Repo(os.getcwd())

        try:
            # Check if the repository has any remotes
            if repo.remotes:
                # Fetch the latest changes from all remotes
                for remote in repo.remotes:
                    remote.fetch()

                # Check if there are any differences between local and remote
                if repo.is_dirty() or (repo.head.is_valid() and repo.head.commit != repo.remotes[0].refs[0].commit):
                    # Pull the latest changes from the first remote
                    repo.remotes[0].pull()
            else:
                print("No remotes found in the repository")
        except GitCommandError as e:
            print(f"Git operation failed: {str(e)}")
            # Continue execution even if Git operations fail

        # Get all files in the repository
        all_files = []
        for root, dirs, files in os.walk(os.getcwd()):
            for file in files:
                relative_path = os.path.relpath(os.path.join(root, file), os.getcwd())
                all_files.append(relative_path.replace('\\', '/'))

        # Filter out any unwanted files or directories
        excluded_patterns = ['.git', '__pycache__', '.vscode', '.idea', '.papertlab.tags.cache.v3', '.papertlab.chat.history.md']
        filtered_files = [f for f in all_files if not any(pattern in f for pattern in excluded_patterns)]

        # Create a file structure
        file_structure = get_file_structure(filtered_files)

        # Generate a hash of the file structure
        current_hash = hashlib.md5(json.dumps(file_structure, sort_keys=True).encode()).hexdigest()

        # Check if the file structure has changed
        if current_hash != last_file_structure_hash:
            last_file_structure_hash = current_hash
            return jsonify({"files": file_structure, "changed": True}), 200
        else:
            return jsonify({"changed": False}), 200

    except InvalidGitRepositoryError:
        print("Not a valid Git repository")
        # If it's not a Git repo, just return the current file structure
        file_structure = get_file_structure(os.listdir(os.getcwd()))
        return jsonify({"files": file_structure, "changed": True}), 200
    except Exception as e:
        print(f"Error in check_new_files: {str(e)}")
        # If an error occurs, return a JSON response with the error
        return jsonify({"error": f"Error in check_new_files: {str(e)}", "changed": False}), 500


def get_file_structure(files):
    file_structure = {}
    for file in files:
        parts = Path(file).parts
        current = file_structure
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = file
    return file_structure

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False, threaded=True)
