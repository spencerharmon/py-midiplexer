from nubia.internal.commands.builtin import Exit
from nubia.internal import context

class CustomExit(Exit):
    def run_interactive(self, cmd, args, raw):
        ctx = context.get_context()
        ctx.midiplexer.shutdown()
        super().run_interactive(cmd, args, raw)
