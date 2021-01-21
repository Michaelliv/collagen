import subprocess


def exec_shell(*commands: str):
    for command in commands:
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
        process.wait()
