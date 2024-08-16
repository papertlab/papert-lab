# Papertlab: Your AI Pair Programmer

![Logo](https://github.com/papertlab/papert-lab/blob/main/docs/static/logo.png)

Papertlab is your AI-powered pair programmer that lets you seamlessly collaborate with Large Language Models (LLMs) to edit code in your local Git repository or any other codebases. Whether you're starting a new project or working with an existing Git repository, Papertlab is here to help. It works best with Claude 3.5 Sonnet and GPT-4o.

## Features

- **Run Papertlab with the files you want to edit:** Select specific files to focus on during your coding session.
- **Add new features or test cases:** Papertlab can help you implement new features or write test cases for your existing code.
- **Refactor your code:** Easily refactor your codebase with the assistance of Papertlab.
- **Update documentation:** Automatically update your documentation based on code changes or other inputs.
- **Initialize and maintain Git repositories:** Papertlab will initialize your Git repository for new projects and manage it efficiently.
- **Automatic Git commits:** Papertlab automatically commits changes with sensible commit messages.
- **Support for multiple programming languages:** Works with Python, JavaScript, TypeScript, PHP, HTML, CSS, and more.
- **Best with GPT-4o & Claude 3.5 Sonnet:** Optimized for these LLMs to provide the best code suggestions and improvements.
- **Edit multiple files at once:** Handles complex requests by editing multiple files simultaneously.
- **Works well in larger codebases:** Utilizes a map of your entire Git repository to ensure context-aware suggestions and changes.

## Installation

### Prerequisites

Papertlab requires Universal Ctags for parsing code and generating tags. Follow the instructions below to install Ctags on your operating system.

### Installing Universal Ctags

#### For macOS and Linux (using Homebrew):

1. **Install Homebrew (if not already installed):**
   - **macOS:**
     ```bash
     /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
     ```
   - **Linux:**
     Follow the [Linuxbrew installation instructions](https://docs.brew.sh/Homebrew-on-Linux).

2. **Install Universal Ctags:**
   ```bash
   brew install --HEAD universal-ctags/universal-ctags/universal-ctags
   ```

#### For Windows (using Chocolatey):

1. **Install Chocolatey:**
   Open an elevated Command Prompt and run:
   ```powershell
   Set-ExecutionPolicy Bypass -Scope Process -Force; `
   [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; `
   iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
   ```

2. **Install Universal Ctags:**
   ```bash
   choco install ctags
   ```

### Verify Ctags Installation

After installation, verify that Ctags is correctly installed by running the following command in your terminal or command prompt:

```bash
ctags --version
```

## Setting Up Papertlab

1. **Create a Virtual Environment:**

   Create and activate a virtual environment to keep your dependencies isolated:

   macOS/Linux:
   ```bash
   python3 -m venv papertlab-env
   source papertlab-env/bin/activate
   ```

   Windows:
   ```bash
   python -m venv papertlab-env
   .\papertlab-env\Scripts\activate
   ```

2. **Install Papertlab:**

   Install the Papertlab package using pip:
   ```bash
   pip install papert-lab
   ```

3. **Run Papertlab:**

   Navigate to your local Git repository or the directory you want to work in, then run:
   ```bash
   papertlab
   ```

4. **Access Papertlab in Your Browser:**

   Open your web browser and go to `http://127.0.0.1:5000/` to access the Papertlab interface.

    ![Demo](https://github.com/papertlab/papert-lab/blob/main/docs/static/demo.gif) 


## Contributing

Contributions are welcome! Please refer to the CONTRIBUTION.md file for guidelines on how to contribute to the project.


## Questions and Support

If you have any questions or need support, please don't hesitate to reach out:

- Email: azhar@papert.in
- LinkedIn: [https://www.linkedin.com/in/mohamed-azharudeen/](https://www.linkedin.com/in/mohamed-azharudeen/)
