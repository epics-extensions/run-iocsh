import re


def get_module_dir(logtext: str, module: str) -> str:
    match = re.search(f"Module {module} version " + r".* found in (.*)\n", logtext)
    return match.group(1) if match else ""
