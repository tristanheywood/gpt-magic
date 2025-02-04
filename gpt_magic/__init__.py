import os

from IPython.core.magic import Magics, cell_magic, line_magic, magics_class
from .gpt_state import GPTMagicState
from .gpt_command import gpt_command

from .displays import get_registered_display
from .subcommands import ChatCommand, ChatModelsBrowserCommand, ConfigCommand

_state = GPTMagicState()

def get_GPTMagicState():
    global _state
    return _state

@magics_class
class IPythonGPT(Magics):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self._context = {
        #     "config": {
        #         "openai_api_key":
        #         os.environ.get("OPENAI_API_KEY")
        #         or globals().get("OPENAI_API_KEY"),
        #         "default_model":
        #         "gpt-3.5-turbo",
        #         "default_system_message":
        #         "You are a python data science coding assistant",
        #     },
        #     "message_history": [],
        # }
        # self.display = get_registered_display()
        self.state = get_GPTMagicState()

    @cell_magic
    @line_magic
    def gpt(self, line, cell=None):
        """
        Invoke GPT on the given cell.

        Run `%gpt --help` for more information.

        Usage (cell mode only):
          %%gpt <prompt>
          %%gpt --login
            Enter your OpenAI API Key.
          %%gpt --code <prompt>
            Generate executable Python code based on <prompt> and put in this cell.
        """
        gpt_command(self.state, line, cell)

    @cell_magic
    def chat(self, line, cell):
        cmd = ChatCommand(self._context)
        result = cmd.execute(line, cell)
        self.display.display(result)

    @line_magic
    def chat_config(self, line):
        cmd = ConfigCommand(self._context)
        result = cmd.execute(line)
        self.display.display(result)

    @line_magic
    def chat_models(self, line):
        cmd = ChatModelsBrowserCommand(self._context)
        result = cmd.execute(line)
        self.display.display(result)


name = "ipython_gpt"


def load_ipython_extension(ipython):
    ipython.register_magics(IPythonGPT)
