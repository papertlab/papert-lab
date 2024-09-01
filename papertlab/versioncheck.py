import os
import sys
import time
from pathlib import Path

import packaging.version

import papertlab
from papertlab import utils
from papertlab.dump import dump  # noqa: F401

VERSION_CHECK_FNAME = Path.home() / ".papertlab" / "caches" / "versioncheck"


def install_from_main_branch(io):
    """
    Install the latest version of papertlab from the main branch of the GitHub repository.
    """
    return utils.check_pip_install_extra(
        io,
        None,
        "Install the development version of papertlab from the main branch?",
        ["--upgrade", "git+https://github.com/papertlab/papert-lab.git"],
    )

def install_upgrade(io):
    """
    Install the latest version of papert-lab from PyPI.
    """
    return utils.check_pip_install_extra(
        io,
        None,
        "Install the latest version of papertlab from PyPI?",
        ["--upgrade", "papert-lab"],
    )

def check_version(io, just_check=False, verbose=False):
    if not just_check and VERSION_CHECK_FNAME.exists():
        day = 60 * 60 * 24
        since = time.time() - os.path.getmtime(VERSION_CHECK_FNAME)
        if 0 < since < day:
            if verbose:
                hours = since / 60 / 60
                io.tool_output(f"Too soon to check version: {hours:.1f} hours")
            return

    # To keep startup fast, avoid importing this unless needed
    import requests

    try:
        response = requests.get("https://pypi.org/pypi/papert-lab/json")
        data = response.json()
        latest_version = data["info"]["version"]
        current_version = papertlab.__version__

        if just_check or verbose:
            io.tool_output(f"Current version: {current_version}")
            io.tool_output(f"Latest version: {latest_version}")

        is_update_available = packaging.version.parse(latest_version) > packaging.version.parse(
            current_version
        )
    except Exception as err:
        io.tool_error(f"Error checking pypi for new version: {err}")
        return False
    finally:
        VERSION_CHECK_FNAME.parent.mkdir(parents=True, exist_ok=True)
        VERSION_CHECK_FNAME.touch()

    if just_check or verbose: 
        if is_update_available:
            io.tool_output("Update available")
        else:
            io.tool_output("No update available")
    
    if just_check:
        return is_update_available

    if not is_update_available:
        return False

    cmd = utils.get_pip_install(["--upgrade", "papert-lab"])

    text = f"Newer papertlab version v{latest_version} is available. To upgrade, run:"

    io.tool_error(text)

    if io.confirm_ask("Run pip install?", subject=" ".join(cmd)):
        success, output = utils.run_install(cmd)
        if success:
            io.tool_output("Re-run papertlab to use new version.")
            sys.exit()
        else:
            io.tool_error(output)

    return True
