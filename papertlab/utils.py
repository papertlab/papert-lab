import itertools
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
import git

from papertlab.dump import dump  # noqa: F401

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp"}


class IgnorantTemporaryDirectory:
    def __init__(self):
        if sys.version_info >= (3, 10):
            self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        else:
            self.temp_dir = tempfile.TemporaryDirectory()

    def __enter__(self):
        return self.temp_dir.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()

    def cleanup(self):
        try:
            self.temp_dir.cleanup()
        except (OSError, PermissionError, RecursionError):
            pass  # Ignore errors (Windows)

    def __getattr__(self, item):
        return getattr(self.temp_dir, item)


class ChdirTemporaryDirectory(IgnorantTemporaryDirectory):
    def __init__(self):
        try:
            self.cwd = os.getcwd()
        except FileNotFoundError:
            self.cwd = None

        super().__init__()

    def __enter__(self):
        res = super().__enter__()
        os.chdir(Path(self.temp_dir.name).resolve())
        return res

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.cwd:
            try:
                os.chdir(self.cwd)
            except FileNotFoundError:
                pass
        super().__exit__(exc_type, exc_val, exc_tb)


class GitTemporaryDirectory(ChdirTemporaryDirectory):
    def __enter__(self):
        dname = super().__enter__()
        self.repo = make_repo(dname)
        return dname

    def __exit__(self, exc_type, exc_val, exc_tb):
        del self.repo
        super().__exit__(exc_type, exc_val, exc_tb)


def make_repo(path=None):
    if not path:
        path = "."
    repo = git.Repo.init(path)
    repo.config_writer().set_value("user", "name", "Test User").release()
    repo.config_writer().set_value("user", "email", "testuser@example.com").release()

    return repo


def is_image_file(file_name):
    """
    Check if the given file name has an image file extension.

    :param file_name: The name of the file to check.
    :return: True if the file is an image, False otherwise.
    """
    file_name = str(file_name)  # Convert file_name to string
    return any(file_name.endswith(ext) for ext in IMAGE_EXTENSIONS)


def safe_abs_path(res):
    "Gives an abs path, which safely returns a full (not 8.3) windows path"
    res = Path(res).resolve()
    return str(res)


def format_content(role, content):
    formatted_lines = []
    for line in content.splitlines():
        formatted_lines.append(f"{role} {line}")
    return "\n".join(formatted_lines)


def format_messages(messages, title=None):
    output = []
    if title:
        output.append(f"{title.upper()} {'*' * 50}")

    for msg in messages:
        output.append("")
        role = msg["role"].upper()
        content = msg.get("content")
        if isinstance(content, list):  # Handle list content (e.g., image messages)
            for item in content:
                if isinstance(item, dict):
                    for key, value in item.items():
                        if isinstance(value, dict) and "url" in value:
                            output.append(f"{role} {key.capitalize()} URL: {value['url']}")
                        else:
                            output.append(f"{role} {key}: {value}")
                else:
                    output.append(f"{role} {item}")
        elif isinstance(content, str):  # Handle string content
            output.append(format_content(role, content))
        function_call = msg.get("function_call")
        if function_call:
            output.append(f"{role} Function Call: {function_call}")

    return "\n".join(output)


def show_messages(messages, title=None, functions=None):
    formatted_output = format_messages(messages, title)
    print(formatted_output)

    if functions:
        dump(functions)


def split_chat_history_markdown(text, include_tool=False):
    messages = []
    user = []
    assistant = []
    tool = []
    lines = text.splitlines(keepends=True)

    def append_msg(role, lines):
        lines = "".join(lines)
        if lines.strip():
            messages.append(dict(role=role, content=lines))

    for line in lines:
        if line.startswith("# "):
            continue
        if line.startswith("> "):
            append_msg("assistant", assistant)
            assistant = []
            append_msg("user", user)
            user = []
            tool.append(line[2:])
            continue
        # if line.startswith("#### /"):
        #    continue

        if line.startswith("#### "):
            append_msg("assistant", assistant)
            assistant = []
            append_msg("tool", tool)
            tool = []

            content = line[5:]
            user.append(content)
            continue

        append_msg("user", user)
        user = []
        append_msg("tool", tool)
        tool = []

        assistant.append(line)

    append_msg("assistant", assistant)
    append_msg("user", user)

    if not include_tool:
        messages = [m for m in messages if m["role"] != "tool"]

    return messages


def get_pip_install(args):
    cmd = [
        sys.executable,
        "-m",
        "pip",
        "install",
    ]
    cmd += args
    return cmd


def run_install(cmd):
    print()
    print("Installing: ", " ".join(cmd))

    try:
        output = []
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )
        spinner = Spinner("Installing...")

        while True:
            char = process.stdout.read(1)
            if not char:
                break

            output.append(char)
            spinner.step()

        spinner.end()
        return_code = process.wait()
        output = "".join(output)

        if return_code == 0:
            print("Installation complete.")
            print()
            return True, output

    except subprocess.CalledProcessError as e:
        print(f"\nError running pip install: {e}")

    print("\nInstallation failed.\n")

    return False, output

class Spinner:
    spinner_chars = itertools.cycle(["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"])

    def __init__(self, text):
        self.text = text
        self.start_time = time.time()
        self.last_update = 0
        self.visible = False

    def step(self):
        current_time = time.time()
        if not self.visible and current_time - self.start_time >= 0.5:
            self.visible = True
            self._step()
        elif self.visible and current_time - self.last_update >= 0.1:
            self._step()
        self.last_update = current_time

    def _step(self):
        if not self.visible:
            return

        print(f"\r{self.text} {next(self.spinner_chars)}\r{self.text} ", end="", flush=True)

    def end(self):
        if self.visible:
            print("\r" + " " * (len(self.text) + 3))

def find_common_root(abs_fnames):
    if len(abs_fnames) == 1:
        return safe_abs_path(os.path.dirname(list(abs_fnames)[0]))
    elif abs_fnames:
        return safe_abs_path(os.path.commonpath(list(abs_fnames)))
    else:
        return safe_abs_path(os.getcwd())

def format_tokens(count):
    if count < 1000:
        return f"{count}"
    elif count < 10000:
        return f"{count / 1000:.1f}k"
    else:
        return f"{round(count / 1000)}k"

def check_pip_install_extra(io, module, prompt, pip_install_cmd):
    if module:
        try:
            __import__(module)
            return True
        except (ImportError, ModuleNotFoundError):
            pass

    cmd = get_pip_install(pip_install_cmd)

    if prompt:
        io.tool_error(prompt)

    if not io.confirm_ask("Run pip install?", default="y", subject=" ".join(cmd)):
        return

    success, output = run_install(cmd)
    if success:
        if not module:
            return
        try:
            __import__(module)
            return True
        except (ImportError, ModuleNotFoundError) as err:
            io.tool_error(str(err))
            pass

    io.tool_error(output)

    print()
    print(f"Failed to install {pip_install_cmd[0]}")


def create_papertlabignore(root_dir):
    papertlabignore_path = os.path.join(root_dir, '.papertlabignore')
    if not os.path.exists(papertlabignore_path):
        default_ignore = """
# Default .papertlabignore file
# Add patterns for files and directories you want papertlab to ignore

# Ignore common development files and directories
.git/
.vscode/
__pycache__/
*.pyc
*.pyo
*.pyd

# Ignore large binary files
*.zip
*.tar.gz
*.rar

# Ignore sensitive information
.env
secrets.json

# Add your custom ignore patterns below
"""
        with open(papertlabignore_path, 'w') as f:
            f.write(default_ignore.strip())
        print(f"Created .papertlabignore file at {papertlabignore_path}")
    else:
        print()

def create_papertlab_readonly(root_dir):
    readonly_path = os.path.join(root_dir, '.papertlab_readonly')
    if not os.path.exists(readonly_path):
        default_readonly = """
# .papertlab_readonly file
# Add patterns for files and directories you want papertlab to treat as read-only

# Examples:
# docs/
# config.ini
# *.log

# Add your patterns below:
"""
        with open(readonly_path, 'w') as f:
            f.write(default_readonly.strip())
        print(f"Created .papertlab_readonly file at {readonly_path}")
    else:
        print()

def extract_updated_code(result):
    # This function should extract the updated code from the result
    # You might need to adjust this based on the exact format of your result
    # This is a simplified example
    start_marker = "```python"
    end_marker = "```"
    start_index = result.find(start_marker)
    end_index = result.find(end_marker, start_index + len(start_marker))
    if start_index != -1 and end_index != -1:
        return result[start_index + len(start_marker):end_index].strip()
    return None

def execute_command(cmd):
    """
    Executes a command in the command line and returns the output and error messages.

    Parameters:
    cmd (str): The command to execute.

    Returns:
    tuple: A tuple containing the command's standard output and standard error.
    """
    try:
        result = subprocess.run(cmd, shell=True, check=True, text=True, capture_output=True)
        return result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return e.stdout, e.stderr

def get_available_models():
    models = []
    if 'ANTHROPIC_API_KEY' in os.environ:
        models.extend([
            "claude-3-5-sonnet-20240620",
            "claude-3-opus-20240229",
            "claude-3-haiku-20240307",
        ])
    if 'OPENAI_API_KEY' in os.environ:
        models.extend([
            "gpt-4o",
            "gpt-4-0613",
            "gpt-4-turbo-preview",
            "gpt-4-1106-preview",
            "gpt-3.5-turbo",
        ])
    if 'GEMINI_API_KEY' in os.environ:
        models.extend([
            "gemini-1.5-pro",
            "gemini-1.5-pro-latest",
        ])
    if 'GROQ_API_KEY' in os.environ:
        models.extend([
            "llama3-70b-8192",
        ])
    if 'OLLAMA_API_BASE' in os.environ:
        models.extend([
            "ollama/codeqwen",
            "ollama/codellama",
            "ollama/codestral",
            "ollama/codegemma",
        ])
    if 'COHERE_API_KEY' in os.environ:
        models.extend([
            "command-r-plus",
        ])
    return models

