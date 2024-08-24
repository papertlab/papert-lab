# In agents/inline_coder.py

from .base_coder import Coder
from .inline_prompts import InlinePrompts

class InlineCoder(Coder):
    """A coder that suggests inline changes to selected code."""
    edit_format = "inline"
    gpt_prompts = InlinePrompts()

    def cmd_inline(self, args):
        "Suggest inline changes to selected code"
        selected_code, edit_request = args.split('\n', 1)
        message = f"""For the following code:

<<<<<<< SEARCH
{selected_code}
=======
{selected_code}
>>>>>>> REPLACE

Suggested change: {edit_request}

Provide the modified code using the SEARCH/REPLACE format. 
The SEARCH section should contain the exact original code.
The REPLACE section should contain the entire code with your modifications.
Make only the necessary changes in the REPLACE section.
Preserve all indentation and formatting."""

        result = self.run(message)
        return result, self

    def get_edits(self, mode="update"):
        content = self.partial_response_content
        edits = self.extract_search_replace_blocks(content)
        return edits

    def apply_edits(self, edits):
        # This method is left empty as we don't want to automatically apply changes
        pass

    def extract_search_replace_blocks(self, content):
        edits = []
        lines = content.split('\n')
        current_block = {'search': [], 'replace': []}
        current_section = None

        for line in lines:
            if line.strip() == '<<<<<<< SEARCH':
                current_section = 'search'
            elif line.strip() == '=======':
                current_section = 'replace'
            elif line.strip() == '>>>>>>> REPLACE':
                if current_block['search'] and current_block['replace']:
                    # Use a placeholder filename if no files are in the chat context
                    filename = self.get_inchat_relative_files()[0] if self.get_inchat_relative_files() else "inline_edit.txt"
                    edits.append((
                        filename,
                        '\n'.join(current_block['search']),
                        '\n'.join(current_block['replace'])
                    ))
                current_block = {'search': [], 'replace': []}
                current_section = None
            elif current_section:
                current_block[current_section].append(line)

        return edits