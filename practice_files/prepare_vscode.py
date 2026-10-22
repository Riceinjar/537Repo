"""Prepare a separate, visible VS Code exam profile before the exam; no Docker."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

PYTHON_TOOLS = ("ms-python.python", "ms-python.debugpy")
MACOS_USER_DATA_MAX_BYTES = 80  # Leave room for VS Code's Unix socket filename.


def macos_code_candidates():
    return [
        app / "Contents/Resources/app/bin/code"
        for app in (
            Path("/Applications/Visual Studio Code.app"),
            Path.home() / "Applications/Visual Studio Code.app",
        )
    ]


def choose_code(requested=None):
    """Find the CLI launcher without changing PATH or application permissions."""
    if requested:
        candidate = Path(requested).expanduser()
        if candidate.suffix.lower() == ".app":
            candidate = candidate / "Contents/Resources/app/bin/code"
        found = shutil.which(str(candidate))
        if found:
            return found
        if candidate.is_file():
            return str(candidate.absolute())
        raise ValueError(
            f"VS Code launcher not found: {candidate}. "
            "Use --code with the launcher file, such as "
            "bin/code.cmd on Windows or "
            '"/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code" on macOS.'
        )
    found = shutil.which("code")
    if found:
        return found
    if sys.platform == "darwin":
        for candidate in macos_code_candidates():
            if candidate.is_file():
                return str(candidate)
    raise ValueError(
        "VS Code's code launcher was not found. Use --code with its full path. "
        "On macOS, open VS Code, press Cmd+Shift+P, run "
        "Shell Command: Install 'code' command in PATH, then open a new terminal "
        'and retry. Alternatively use --code "/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code".'
    )


def profile_directory(repo):
    work = repo / "part2_exam_files"
    if (work / "submission.py").is_file():
        if work.is_symlink() or not work.resolve().is_relative_to(repo):
            raise ValueError("part2_exam_files must be inside the homework repository.")
        return work / ".me537_exam_profile"
    return repo / ".me537_exam_profile"


def user_data_directory(repo, profile):
    """Keep macOS's VS Code IPC socket below its path-length limit."""
    local = profile / "user-data"
    if (
        sys.platform != "darwin"
        or len(os.fsencode(str(local))) <= MACOS_USER_DATA_MAX_BYTES
    ):
        return local
    digest = hashlib.sha256(os.fsencode(str(repo))).hexdigest()[:16]
    short = Path.home() / ".me537" / digest
    if len(os.fsencode(str(short))) > MACOS_USER_DATA_MAX_BYTES:
        raise ValueError(
            "Your macOS home path is too long for the isolated VS Code profile. "
            "Contact the instructor for a shorter user-data location."
        )
    return short


def profile_flags(repo, profile):
    return [
        "--user-data-dir",
        str(user_data_directory(repo, profile)),
        "--extensions-dir",
        str(profile / "extensions"),
    ]


def choose_python(repo, requested=None):
    if requested:
        chosen = Path(requested).expanduser()
        if not chosen.is_absolute():
            chosen = repo / chosen
        if not chosen.is_file():
            raise ValueError(
                f"Python interpreter not found: {chosen}. Use --python with the path to the Python interpreter in your virtual environment."
            )
        # Keep the environment's executable path: POSIX venv Python is often a
        # symlink, and resolving it would select the base interpreter instead.
        return chosen.absolute()
    workspace = profile_directory(repo) / "ME537.code-workspace"
    if workspace.is_file():
        previous = (
            json.loads(workspace.read_text(encoding="utf-8"))
            .get("settings", {})
            .get("python.defaultInterpreterPath")
        )
        if previous and Path(previous).is_file():
            return Path(previous).absolute()
    # A repository-local course environment is preferable to an unactivated
    # system Python used just to run this setup script.
    for folder in (".venv", "venv"):
        candidate = (
            repo
            / folder
            / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        )
        if candidate.is_file():
            return candidate.absolute()
    return Path(sys.executable).absolute()


def prepare(repo, practice_demo=False, python=None):
    repo = Path(repo).resolve()
    if not (repo / "src" / "byu_robomanip" / "kinematics.py").is_file():
        raise ValueError(
            "Select your homework repository, containing src/byu_robomanip."
        )
    if practice_demo:
        demo = repo / "exam_helpers" / "practice_motion.py"
        if (
            demo.is_symlink()
            or demo.parent.is_symlink()
            or not demo.resolve().is_relative_to(repo)
        ):
            raise ValueError(
                "Practice demo paths must not use links outside the working copy."
            )
        if demo.exists():
            # The exercise explicitly asks students to edit this file. Rerunning
            # setup must keep their copy and reopen the same prepared workspace.
            if not demo.is_file():
                raise ValueError("exam_helpers/practice_motion.py must be a file.")
        else:
            demo.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(Path(__file__).with_name("practice_motion.py"), demo)
    profile = profile_directory(repo)
    interpreter = choose_python(repo, python)
    profile.mkdir(exist_ok=True)
    (profile / ".gitignore").write_text("*\n", encoding="utf-8")
    settings = {
        "chat.disableAIFeatures": True,
        "editor.inlineSuggest.enabled": False,
        "extensions.ignoreRecommendations": True,
        "extensions.autoUpdate": False,
        "extensions.autoCheckUpdates": False,
        "files.autoSave": "afterDelay",
        "files.autoSaveDelay": 1000,
        "python.defaultInterpreterPath": str(interpreter),
        "python.terminal.activateEnvironment": True,
    }
    workspace = profile / "ME537.code-workspace"
    workspace.write_text(
        json.dumps(
            {
                "folders": [
                    {"path": os.path.relpath(repo, profile).replace("\\", "/")}
                ],
                "settings": settings,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    # The new Python Environments activation setting is user-scoped. Write it
    # only into THIS isolated environment's settings, preserving other values.
    data_dir = user_data_directory(repo, profile)
    legacy_settings = profile / "user-data/User/settings.json"
    user_settings = data_dir / "User/settings.json"
    if data_dir != profile / "user-data":
        marker = data_dir / ".me537-repo"
        if (
            data_dir.parent.is_symlink()
            or data_dir.is_symlink()
            or marker.is_symlink()
            or (marker.exists() and marker.read_text(encoding="utf-8") != str(repo) + "\n")
        ):
            raise ValueError(
                "The short VS Code user-data directory belongs to another repository."
            )
        if data_dir.exists() and not marker.exists() and any(data_dir.iterdir()):
            raise ValueError(
                "The short VS Code user-data directory is not an ME537 profile."
            )
        data_dir.mkdir(parents=True, exist_ok=True)
        marker.write_text(str(repo) + "\n", encoding="utf-8")
    user_settings.parent.mkdir(parents=True, exist_ok=True)
    values = (
        json.loads(user_settings.read_text(encoding="utf-8"))
        if user_settings.exists()
        else json.loads(legacy_settings.read_text(encoding="utf-8"))
        if legacy_settings.is_file()
        else {}
    )
    values.update(
        {
            "python-envs.terminal.autoActivationType": "command",
            "python.terminal.activateEnvironment": True,
        }
    )
    user_settings.write_text(json.dumps(values, indent=2) + "\n", encoding="utf-8")
    return workspace, profile_flags(repo, profile)


def installed_extensions(code, flags):
    result = subprocess.run(
        [code, *flags, "--list-extensions", "--show-versions"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    versions = {}
    for line in result.stdout.splitlines():
        name, _, version = line.strip().partition("@")
        if name:
            versions[name.lower()] = version or "installed"
    return versions


def ensure_python_tools(code, flags, install=False):
    versions = installed_extensions(code, flags)
    for name in PYTHON_TOOLS:
        if name not in versions and install:
            print(
                f"Installing {name} for Python Run/Debug (one-time Marketplace download)...",
                flush=True,
            )
            subprocess.run(
                [code, *flags, "--install-extension", name], check=True, timeout=120
            )
            versions = installed_extensions(code, flags)
    missing = [name for name in PYTHON_TOOLS if name not in versions]
    if missing:
        raise ValueError(
            "Python Run/Debug tools are missing: "
            + ", ".join(missing)
            + ". Run setup with --launch to install them, or use --skip-python-tools for recorder-only diagnostics."
        )
    return versions


def launch_workspace(code, flags, workspace):
    command = [code, *flags, "--new-window", str(workspace)]
    result = subprocess.run(
        command, capture_output=True, encoding="utf-8", errors="replace", timeout=30
    )
    if result.returncode:
        raise ValueError(
            f"VS Code launch request failed (exit {result.returncode}).\n"
            + result.stdout[-2000:]
            + result.stderr[-4000:]
        )
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip(), file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument(
        "--python",
        type=Path,
        help="Python interpreter in your virtual environment; default is the saved selection, repo .venv/venv, or running Python",
    )
    parser.add_argument(
        "--skip-python-tools",
        action="store_true",
        help="Recorder-only diagnostics: do not install/check Python Run/Debug tools",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check recorder installation in the prepared environment without opening VS Code",
    )
    parser.add_argument(
        "--practice-demo",
        action="store_true",
        help="Copy the supplied two-link demo into exam_helpers/ for practice only",
    )
    parser.add_argument(
        "--vsix", type=Path, help="Faculty-provided me537-exam-recorder.vsix"
    )
    parser.add_argument(
        "--code",
        help="VS Code CLI launcher or macOS .app path; otherwise search PATH and standard macOS Applications folders",
    )
    parser.add_argument(
        "--launch", action="store_true", help="Open the visible exam profile"
    )
    args = parser.parse_args()
    repo = Path(args.repo).resolve()
    script = Path(__file__).absolute()
    try:
        script = script.relative_to(repo)
    except ValueError:
        pass
    script_argument = f'"{script.as_posix()}"'
    recorder_argument = f'"{script.with_name("me537-exam-recorder.vsix").as_posix()}"'
    demo = repo / "exam_helpers/practice_motion.py"
    demo_existed = demo.exists()
    try:
        code = (
            choose_code(args.code)
            if args.code or args.vsix or args.launch or args.check
            else None
        )
        if args.check:
            profile = profile_directory(repo)
            workspace = profile / "ME537.code-workspace"
            if not workspace.is_file():
                raise ValueError(
                    "No prepared environment was found. Run the setup command in Step 3 first."
                )
            flags = profile_flags(repo, profile)
            if not Path(flags[1]).is_dir():
                raise ValueError(
                    "The VS Code user-data directory is missing. "
                    "Rerun setup before --check."
                )
            if Path(flags[1]) != profile / "user-data":
                marker = Path(flags[1]) / ".me537-repo"
                if not marker.is_file() or marker.read_text(encoding="utf-8") != str(repo) + "\n":
                    raise ValueError(
                        "The short VS Code user-data directory does not belong to this repository."
                    )
        else:
            workspace, flags = prepare(repo, args.practice_demo, args.python)
        print("ME 537: VS Code setup", flush=True)
        print("Workspace:", workspace)
        print("VS Code user data:", flags[1])
        if code:
            print("VS Code launcher:", code)
        interpreter = (
            json.loads(workspace.read_text(encoding="utf-8"))
            .get("settings", {})
            .get("python.defaultInterpreterPath")
        )
        print(
            "Configured Python interpreter:",
            interpreter or "not configured; rerun setup with --python",
        )
        if args.practice_demo:
            print(
                "Practice source:",
                (
                    "existing file kept (your edits are preserved)."
                    if demo_existed
                    else "copied into exam_helpers/practice_motion.py."
                ),
            )
        if args.vsix:
            print(
                "Installing the recorder in the separate ME537 environment...",
                flush=True,
            )
            subprocess.run(
                [
                    code,
                    *flags,
                    "--install-extension",
                    str(args.vsix.resolve()),
                    "--force",
                ],
                check=True,
                timeout=60,
            )
        if args.vsix or args.launch or args.check:
            versions = installed_extensions(code, flags)
            version = versions.get("byu-me537.me537-exam-recorder")
            if not version:
                raise ValueError(
                    "The recorder is not installed in this separate VS Code environment. "
                    f"Run the Step 3 setup command with --vsix {recorder_argument} first."
                )
            print(f"PASS: Recorder {version} is installed in this ME537 environment.")
            if not args.skip_python_tools:
                versions = ensure_python_tools(code, flags, install=not args.check)
                for name in PYTHON_TOOLS:
                    print(f"PASS: {name} {versions[name]} is installed for Run/Debug.")
        print("\nIn the ME537 VS Code window:")
        print(
            "  1. If Restricted Mode appears at the bottom, click it, then Trust for your homework repository folder."
        )
        print("  2. Press Ctrl+Shift+P (Windows/Linux) or Cmd+Shift+P (macOS).")
        print("  3. Type ME537 and select Start Disclosed Exam Session.")
        print("  4. Accept the disclosure. The status changes from OFF to ON.")
        print("These are Command Palette actions, not terminal commands.")
        print("Recording starts only after your consent in VS Code.")
        print("\nFor Python Run/Debug and terminals:")
        print(
            "  Open a .py file. Python Run/Debug controls come from the Microsoft Python tools."
        )
        print(
            "  Use Python: Select Interpreter from the Command Palette and choose the Python interpreter in your virtual environment."
        )
        print(
            "  Close old terminal tabs and open a NEW terminal so environment activation can run."
        )
        print('  Verify: python -c "import sys; print(sys.executable)"')
        print(
            "  Expected: the path points to the Python interpreter in your virtual environment."
        )
        print("\nTo reopen the SAME environment later, run:")
        code_argument = f' --code "{code}"' if args.code else ""
        print(f"  python {script_argument} --repo . --launch{code_argument}")
        print(
            "Opening ME537.code-workspace normally may use your usual extension storage."
        )
        if args.launch:
            print("\nRequesting the separate ME537 window...", flush=True)
            launch_workspace(code, flags, workspace)
            print(
                "VS Code accepted the launch request. Look for the ME537 workspace window."
            )
            print(
                "Confirm that window shows the ME537 recorder in its status bar or Command Palette."
            )
            if sys.platform == "darwin":
                print(
                    "If it is not visible, press Control+Up Arrow for Mission Control and check other desktops."
                )
                print(
                    "If no ME537 window appears, rerun the reopening command from macOS Terminal or iTerm."
                )
        elif not args.check:
            print(
                "Setup files prepared. Add --launch to open the separate ME537 window."
            )
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"\nSETUP FAILED: {error}", file=sys.stderr)
        if isinstance(error, FileNotFoundError):
            print(
                "Use --code with the full launcher path: bin/code.cmd on Windows, "
                '"/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code" '
                "on macOS, or your installed code command on Linux.",
                file=sys.stderr,
            )
        print(
            "Your existing practice source and recordings have not been replaced.",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
