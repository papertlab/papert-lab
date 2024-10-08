import os
import time
from pathlib import Path, PurePosixPath

import git
import pathspec

from papertlab import prompts, utils
from papertlab.sendchat import simple_send_with_retries

from .dump import dump  # noqa: F401


class UnableToCountRepoFiles(Exception):
    pass

class GitRepo:
    repo = None
    papertlab_ignore_file = None
    papertlab_ignore_spec = None
    papertlab_ignore_ts = 0
    papertlab_ignore_last_check = 0
    subtree_only = False
    ignore_file_cache = {}

    def __init__(
        self,
        io,
        fnames,
        git_dname,
        papertlab_ignore_file=None,
        models=None,
        attribute_author=True,
        attribute_committer=True,
        attribute_commit_message_author=False,
        attribute_commit_message_committer=False,
        commit_prompt=None,
    ):
        self.io = io

        self.models = models

        self.normalized_path = {}
        self.tree_files = {}

        self.attribute_author = attribute_author
        self.attribute_committer = attribute_committer
        self.attribute_commit_message_author = attribute_commit_message_author
        self.attribute_commit_message_committer = attribute_commit_message_committer
        self.commit_prompt = commit_prompt


        self.ignore_file_cache = {}

        if git_dname:
            check_fnames = [git_dname]
        elif fnames:
            check_fnames = fnames
        else:
            check_fnames = ["."]

        repo_paths = []
        for fname in check_fnames:
            fname = Path(fname)
            fname = fname.resolve()

            if not fname.exists() and fname.parent.exists():
                fname = fname.parent

            try:
                repo_path = git.Repo(fname, search_parent_directories=True).working_dir
                repo_path = utils.safe_abs_path(repo_path)
                repo_paths.append(repo_path)
            except git.exc.InvalidGitRepositoryError:
                pass
            except git.exc.NoSuchPathError:
                pass

        num_repos = len(set(repo_paths))

        if num_repos == 0:
            raise FileNotFoundError
        if num_repos > 1:
            self.io.tool_error("Files are in different git repos.")
            raise FileNotFoundError

        # https://github.com/gitpython-developers/GitPython/issues/427
        self.repo = git.Repo(repo_paths.pop(), odbt=git.GitDB)
        self.root = utils.safe_abs_path(self.repo.working_tree_dir)

        self.papertlab_ignore_file = Path(self.root) / '.papertlabignore'
   
        self.readonly_file = Path(self.root) / '.papertlab_readonly'
        self.readonly_spec = None
        self.readonly_ts = 0
        self.previous_readonly_files = set()
        self.refresh_readonly_spec()

    def refresh_readonly_spec(self):
        if not self.readonly_file.is_file():
            self.readonly_spec = None
            self.previous_readonly_files.clear()
            return

        mtime = self.readonly_file.stat().st_mtime
        if mtime != self.readonly_ts:
            self.readonly_ts = mtime
            lines = self.readonly_file.read_text().splitlines()
            self.readonly_spec = pathspec.PathSpec.from_lines(
                pathspec.patterns.GitWildMatchPattern,
                lines,
            )
            
            # Update the set of read-only files
            new_readonly_files = set(self.get_readonly_files())
            files_to_remove = self.previous_readonly_files - new_readonly_files
            self.previous_readonly_files = new_readonly_files
            
            return files_to_remove
        
        return set()

    def get_readonly_files(self):
        if not self.readonly_spec:
            return []
        
        all_files = self.get_tracked_files()
        return [f for f in all_files if self.readonly_spec.match_file(f)]
    
    def is_readonly(self, path):
        self.refresh_readonly_spec()
        if not self.readonly_spec:
            return False
        
        normalized_path = self.normalize_path(path)
        return self.readonly_spec.match_file(normalized_path)

    def commit(self, fnames=None, context=None, message=None, papertlab_edits=False):
        if not fnames and not self.repo.is_dirty():
            return

        diffs = self.get_diffs(fnames)
        if not diffs:
            return

        if message:
            commit_message = message
        else:
            commit_message = self.get_commit_message(diffs, context)

        if papertlab_edits and self.attribute_commit_message_author:
            commit_message = "papertlab: " + commit_message
        elif self.attribute_commit_message_committer:
            commit_message = "papertlab: " + commit_message

        if not commit_message:
            commit_message = "(no commit message provided)"

        full_commit_message = commit_message
        # if context:
        #    full_commit_message += "\n\n# papertlab chat conversation:\n\n" + context

        cmd = ["-m", full_commit_message, "--no-verify"]
        if fnames:
            fnames = [str(self.abs_root_path(fn)) for fn in fnames]
            for fname in fnames:
                self.repo.git.add(fname)
            cmd += ["--"] + fnames
        else:
            cmd += ["-a"]

        original_user_name = self.repo.config_reader().get_value("user", "name")
        original_committer_name_env = os.environ.get("GIT_COMMITTER_NAME")
        committer_name = f"{original_user_name} (papertlab)"

        if self.attribute_committer:
            os.environ["GIT_COMMITTER_NAME"] = committer_name

        if papertlab_edits and self.attribute_author:
            original_auther_name_env = os.environ.get("GIT_AUTHOR_NAME")
            os.environ["GIT_AUTHOR_NAME"] = committer_name

        self.repo.git.commit(cmd)
        commit_hash = self.repo.head.commit.hexsha[:7]
        self.io.tool_output(f"Commit {commit_hash} {commit_message}", bold=True)

        # Restore the env

        if self.attribute_committer:
            if original_committer_name_env is not None:
                os.environ["GIT_COMMITTER_NAME"] = original_committer_name_env
            else:
                del os.environ["GIT_COMMITTER_NAME"]

        if papertlab_edits and self.attribute_author:
            if original_auther_name_env is not None:
                os.environ["GIT_AUTHOR_NAME"] = original_auther_name_env
            else:
                del os.environ["GIT_AUTHOR_NAME"]

        return commit_hash, commit_message

    def get_rel_repo_dir(self):
        try:
            return os.path.relpath(self.repo.git_dir, os.getcwd())
        except ValueError:
            return self.repo.git_dir

    def get_commit_message(self, diffs, context):
        diffs = "# Diffs:\n" + diffs

        content = ""
        if context:
            content += context + "\n"
        content += diffs

        system_content = self.commit_prompt or prompts.commit_system
        messages = [
            dict(role="system", content=system_content),
            dict(role="user", content=content),
        ]

        commit_message = None
        for model in self.models:
            num_tokens = model.token_count(messages)
            max_tokens = model.info.get("max_input_tokens") or 0
            if max_tokens and num_tokens > max_tokens:
                continue
            commit_message = simple_send_with_retries(
                model.name, messages, extra_headers=model.extra_headers
            )
            if commit_message:
                break

        if not commit_message:
            self.io.tool_error("Failed to generate commit message!")
            return

        commit_message = commit_message.strip()
        if commit_message and commit_message[0] == '"' and commit_message[-1] == '"':
            commit_message = commit_message[1:-1].strip()

        return commit_message

    def get_diffs(self, fnames=None):
        # We always want diffs of index and working dir

        current_branch_has_commits = False
        try:
            active_branch = self.repo.active_branch
            try:
                commits = self.repo.iter_commits(active_branch)
                current_branch_has_commits = any(commits)
            except git.exc.GitCommandError:
                pass
        except TypeError:
            pass

        if not fnames:
            fnames = []

        diffs = ""
        for fname in fnames:
            if not self.path_in_repo(fname):
                diffs += f"Added {fname}\n"

        if current_branch_has_commits:
            args = ["HEAD", "--"] + list(fnames)
            diffs += self.repo.git.diff(*args)
            return diffs

        wd_args = ["--"] + list(fnames)
        index_args = ["--cached"] + wd_args

        diffs += self.repo.git.diff(*index_args)
        diffs += self.repo.git.diff(*wd_args)

        return diffs

    def diff_commits(self, pretty, from_commit, to_commit):
        args = []
        if pretty:
            args += ["--color"]
        else:
            args += ["--color=never"]

        args += [from_commit, to_commit]
        diffs = self.repo.git.diff(*args)

        return diffs

    def get_tracked_files(self):
        if not self.repo:
            return []

        try:
            try:
                commit = self.repo.head.commit
            except ValueError:
                commit = None

            files = set()
            if commit:
                if commit in self.tree_files:
                    files = self.tree_files[commit]
                else:
                    for blob in commit.tree.traverse():
                        if blob.type == "blob":  # blob is a file
                            files.add(blob.path)
                    files = set(self.normalize_path(path) for path in files)
                    self.tree_files[commit] = set(files)

            # Add staged files
            index = self.repo.index
            staged_files = [path for path, _ in index.entries.keys()]

            files.update(self.normalize_path(path) for path in staged_files)

            # convert to appropriate os.sep, since git always normalizes to /
            res = [fname for fname in files if not self.ignored_file(fname)]

            return res
        except Exception as e:
            raise UnableToCountRepoFiles(f"Error getting tracked files: {str(e)}")
    

    def normalize_path(self, path):
        orig_path = path
        res = self.normalized_path.get(orig_path)
        if res:
            return res

        path = str(Path(PurePosixPath((Path(self.root) / path).relative_to(self.root))))
        self.normalized_path[orig_path] = path
        return path

    def refresh_papertlab_ignore(self):
        if not self.papertlab_ignore_file:
            return

        current_time = time.time()
        if current_time - self.papertlab_ignore_last_check < 1:
            return

        self.papertlab_ignore_last_check = current_time

        if not self.papertlab_ignore_file.is_file():
            return

        mtime = self.papertlab_ignore_file.stat().st_mtime
        if mtime != self.papertlab_ignore_ts:
            self.papertlab_ignore_ts = mtime
            self.ignore_file_cache = {}
            lines = self.papertlab_ignore_file.read_text().splitlines()
            self.papertlab_ignore_spec = pathspec.PathSpec.from_lines(
                pathspec.patterns.GitWildMatchPattern,
                lines,
            )

    def ignored_file(self, fname):
        self.refresh_papertlab_ignore()

        if fname in self.ignore_file_cache:
            return self.ignore_file_cache[fname]

        result = self.ignored_file_raw(fname)
        self.ignore_file_cache[fname] = result
        return result

    def ignored_file_raw(self, fname):

        if not self.papertlab_ignore_file or not self.papertlab_ignore_file.is_file():
            return False

        try:
            fname = self.normalize_path(fname)
        except ValueError:
            return True

        return self.papertlab_ignore_spec.match_file(fname)

    def path_in_repo(self, path):
        if not self.repo:
            return

        tracked_files = set(self.get_tracked_files())
        return self.normalize_path(path) in tracked_files

    def abs_root_path(self, path):
        res = Path(self.root) / path
        return utils.safe_abs_path(res)

    def get_dirty_files(self):
        """
        Returns a list of all files which are dirty (not committed), either staged or in the working
        directory.
        """
        dirty_files = set()

        # Get staged files
        staged_files = self.repo.git.diff("--name-only", "--cached").splitlines()
        dirty_files.update(staged_files)

        # Get unstaged files
        unstaged_files = self.repo.git.diff("--name-only").splitlines()
        dirty_files.update(unstaged_files)

        return list(dirty_files)

    def is_dirty(self, path=None):
        if path and not self.path_in_repo(path):
            return True

        return self.repo.is_dirty(path=path)
    
    def get_head(self):
        try:
            return self.repo.head.commit.hexsha
        except ValueError:
            return None
