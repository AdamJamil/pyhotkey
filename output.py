import os
import pathlib
import run_cmd

root_dir = pathlib.Path(__file__).parent.absolute()
text_editor_path = os.path.join("C:/", "Program Files", "Sublime Text 3", "sublime_text.exe")
schedule_path = os.path.join(root_dir, "IO", "schedule.txt")


def show(content, name):
    file_name = os.path.join(root_dir, "IO", name + ".txt")
    file = open(file_name, "w")
    file.write(content)
    file.close()
    run_cmd.RunCMDThead(text_editor_path + " " + file_name)
