from py_midiplexer.py_midiplexer import Mode

from pygments.token import Token

from nubia import context
from nubia import statusbar
import queue

class NubiaStatusBar(statusbar.StatusBar):
    def __init__(self, context):
        self._last_status = None
        self._first_command = True #exists to change status bar contents after the first command (welcome message)

    def get_rprompt_tokens(self):
        if self._last_status:
            return [(Token.RPrompt, "Error: {}".format(self._last_status))]
        return []

    def set_last_command_status(self, status):
        self._first_command = False
        self._last_status = status

    def get_tokens(self):
        token_list = []
        try:
            status = context.get_context().midiplexer.status_queue.get_nowait()

            spacer = (Token.Spacer, "  ")

            if self._first_command:
                token_list.append((Token.Toolbar, "Welcome to "))

            token_list.append((Token.Toolbar, "py-midiplexer"))

            if self._first_command:
                token_list.append((Token.Toolbar, "!"))

            token_list.append(spacer)

            token_list.append((Token.Toolbar, "Mode: "))
            if status['mode'] == Mode.TRIGGER:
                token_list.append((Token.Warn, "Trigger"))
            elif status['mode'] == Mode.SCENE:
                token_list.append((Token.Info, "Scene"))

            token_list.append(spacer)

            token_list.append((Token.Toolbar, status['filename']))

            if not status['saved']:
                token_list.append((Token.Toolbar, '*'))
            
        except queue.Empty:
            pass

        return token_list

    
