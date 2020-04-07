import argparse
from nubia import PluginInterface, CompletionDataSource
from nubia.internal.cmdbase import AutoCommand
from .nubia_context import NubiaContext
from .nubia_statusbar import NubiaStatusBar
from py_midiplexer.py_midiplexer import MidiPlexer
from py_midiplexer.includes.nubia import commands, exitcmd
import os


class NubiaMidiPlexerPlugin(PluginInterface):
    """
    Nubia plugin for py_midiplexer.
    """
    def __init__(self, muxer: MidiPlexer):
        self.muxer = muxer
        super().__init__()

    def create_context(self):
        return NubiaContext(midiplexer = self.muxer)

    def get_commands(self):
        return [
            AutoCommand(commands.SceneCommands),
            AutoCommand(commands.ControllerCommands),
            AutoCommand(commands.ClientCommands),
            AutoCommand(commands.TriggerMapCommands),
            AutoCommand(commands.SceneMapCommands),
            AutoCommand(commands.save),
            exitcmd.CustomExit()
        ]
    
    def get_opts_parser(self, add_help=True):
        opts_parser = argparse.ArgumentParser(
            description="py_midiplexer. Control one or more midi clients with one or more midi controllers.",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            add_help=add_help,
        )
        
        opts_parser.add_argument(
            "--config", "-c", default=os.environ['HOME']+"/.config/py-midiplexer/config.json", type=str, help="Configuration File"
        )
        opts_parser.add_argument(
            "--verbose",
            "-v",
            action="count",
            default=0,
            help="Increase verbosity, can be specified " "multiple times",
        )
        opts_parser.add_argument(
            "--stderr",
            "-s",
            action="store_true",
            help="By default the logging output goes to a "
            "temporary file. This disables this feature "
            "by sending the logging output to stderr",
        )

        return opts_parser

    def get_status_bar(self, context):
        return NubiaStatusBar(context)
