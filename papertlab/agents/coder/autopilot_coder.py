from .base_coder import Coder
from ..prompts.autopilot_prompts import AutopilotPrompts

class AutopilotCoder(Coder):
    """A coder that automates the process of generating, running, and debugging code."""
    edit_format = "autopilot"
    gpt_prompts = AutopilotPrompts()

    def __init__(self, main_model, io, from_coder=None, **kwargs):
        super().__init__(main_model, io, **kwargs)
        self.input_token = 0
        self.output_token = 0
        self.cost = 0
        self.total_cost = 0
        if from_coder:
            self.abs_fnames = from_coder.abs_fnames
            self.abs_read_only_fnames = from_coder.abs_read_only_fnames
            self.done_messages = from_coder.done_messages
            self.cur_messages = from_coder.cur_messages
            self.commands = from_coder.commands
            self.root = from_coder.root

    def run_autopilot(self, task):
        # Reset usage metrics for this run
        self.input_token = 0
        self.output_token = 0
        self.cost = 0

        # Step 1: Generate code
        code_response, code_coder = self.commands.cmd_code(task)
        self.update_metrics(code_coder)
        self.io.tool_output("Generated code:", code_response)

        # Step 2: Get run instructions
        run_instructions, ask_coder = self.commands.cmd_ask(f"How do I run this code?\n{code_response}")
        self.update_metrics(ask_coder)
        self.io.tool_output("Run instructions:", run_instructions)

        # Step 3: Run the code
        run_result = self.commands.cmd_run(run_instructions)
        self.io.tool_output("Execution result:", run_result)

        # Check for errors and continue the cycle if needed
        if "error" in run_result.lower():
            error_fix_task = f"Fix this error and try again:\n{run_result}"
            return self.run_autopilot(error_fix_task)
        else:
            self.io.tool_output("Autopilot completed successfully. Output is ready.")
            return run_result

    def update_metrics(self, coder):
        self.input_token += coder.input_token
        self.output_token += coder.output_token
        self.cost += coder.cost
        self.total_cost += coder.cost
        self.partial_response_content += coder.partial_response_content

    def get_edits(self, mode="update"):
        task = self.get_cur_message_text()
        result = self.run_autopilot(task)
        return []  # Autopilot doesn't directly edit files

    def apply_edits(self, edits):
        pass  # Autopilot doesn't directly edit files