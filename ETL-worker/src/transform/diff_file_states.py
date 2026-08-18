from pathlib import Path


class DiffFileStates:
    def __init__(
            self,
            relevant_files: list[dict[str, str | Path]],
            processed_data_path: Path | str,
        ) -> None:
        self.relevant_files = relevant_files
        self.processed_data_path = Path(processed_data_path)

        relevant_file_paths_list = map(lambda file: str(file["source"]), self.relevant_files)
        self.relevant_file_paths_set = set(relevant_file_paths_list)

        processed_file_path_list = []
        for file_path in Path(self.processed_data_path).rglob("*"):
            if file_path.is_file():
                processed_file_path_list.append(
                    file_path.relative_to(self.processed_data_path).as_posix().removesuffix('.md')
                )
            
            
        self.processed_file_paths_set = set(processed_file_path_list)

    def get_new_files(self) -> list[dict[str, str | Path]]:
        new_files_set = self.relevant_file_paths_set - self.processed_file_paths_set
        new_files = list(filter(lambda file: str(file["source"]) in new_files_set, self.relevant_files))
        return new_files

    def get_removed_files(self) -> list[dict[str, str | Path]]:
        removed_files_set = self.processed_file_paths_set - self.relevant_file_paths_set
        removed_files = list(removed_files_set)
        return removed_files

    def get_changed_files(self):
        already_processed_files = self.processed_file_paths_set & self.relevant_file_paths_set
        changed_files = list(filter(lambda file: 
            str(file["source"]) in already_processed_files 
            and 
            # Check if the timestamp of the relevant file is different from the timestamp of the processed file
            file["timestamp"] != (self.processed_data_path / f"{str(file['source'])}.md" ).stat().st_mtime
            , self.relevant_files))
        return changed_files