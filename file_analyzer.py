from typing import List

class FileGroup:
    def __init__(self, name: str, files: List[str]):
        self.name = name
        self.files = files

def find_related_files(project_root: str) -> List[FileGroup]:
    """
    Find all files that are related, relative to the project root
    :param project_root: The root directory of the project
    :return: A dictionary of all directories and their files which are related to each other
    """
    ret: List[FileGroup] = []

    return ret
