from nubia import context
from nubia import exceptions
from nubia import eventbus
from pygments.token import Token
from py_midiplexer.py_midiplexer import MidiPlexer


class NubiaContext(context.Context):
    def __init__(self, *args, **kwargs):
        self.midiplexer = kwargs.pop('midiplexer')
        super().__init__(*args, **kwargs)
        
    def on_connected(self, *args, **kwargs):
        pass

    def on_cli(self, cmd, args):
        self.interactive=False
        # dispatch the on connected message
        self.verbose = args.verbose
        self.registry.dispatch_message(eventbus.Message.CONNECTED)

    def on_interactive(self, args):
        self.interactive=True
        self.midiplexer = MidiPlexer(f=args.config)
        self.verbose = args.verbose
        ret = self._registry.find_command("connect").run_cli(args)
        if ret:
            raise exceptions.CommandError("Failed starting interactive mode")
        # dispatch the on connected message
        self.registry.dispatch_message(eventbus.Message.CONNECTED)

    def get_prompt_tokens(self):
        return [(Token.Pound, "py-midiplexer~$")]
