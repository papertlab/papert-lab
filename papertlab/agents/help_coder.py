from ..dump import dump  # noqa: F401
from .base_coder import Coder
from .prompts.help_prompts import HelpPrompts


class HelpCoder(Coder):
    """Interactive help and documentation about papertlab."""
    edit_format = "help"
    gpt_prompts = HelpPrompts()

    def get_edits(self, mode="update"):
        return []

    def apply_edits(self, edits):
        pass
