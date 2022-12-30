import time
from cmd import Cmd

from .inserv import InstrumentServer

def await_close(
    inserv: InstrumentServer,
):
    """Blocks until the InstrumentServer is closed
    """
    while inserv._rpyc_server:
        time.sleep(1)


def inserv_cli(inserv):
    """Run a command-line interface to allow user interaction with the instrument server.
    
    Parameters
    ----------
    inserv: InstrumentServer object
        the instrument server
    """
    cmd_prompt = InservCmdPrompt(inserv)
    try:
        cmd_prompt.cmdloop()
    except KeyboardInterrupt:
        print('Stopping instrument server...')
        inserv.stop()

class InservCmdPrompt(Cmd):
    """Instrument server shell prompt processor"""

    intro = 'Welcome to the instrument server shell.   Type help or ? to list commands.'
    prompt = '(inserv) '

    def __init__(self, inserv: InstrumentServer):
        super().__init__()
        self.inserv = inserv

    def cmdloop(self, intro=None) -> None:
        print("cmdloop")
        return super().cmdloop(intro)

    def emptyline(self) -> bool:
        """When no command is entered."""
        pass

    def do_list(self, arg_string: str):
        """List all the available devices."""
        if arg_string:
            print('Expected 0 args')
            return
        for d, _ in self.inserv._devices.values():
            print(d)

    def do_del(self, arg_string: str):
        """Delete a device\narg 1: <string> the device name."""
        if not arg_string:
            print('Expected 1 arg: device name')
            return
        args = arg_string.split(' ')
        for dev_name in args:
            try:
                self.inserv._remove(dev_name)
            except Exception as exc:
                print(f'Failed to delete device "{dev_name}"')
                return

    def do_restart(self, arg_string: str):
        """Restart a device\narg 1: <string> the device name"""
        if not arg_string:
            print('Expected 1 arg: device name')
            return
        args = arg_string.split(' ')
        for dev_name in args:
            try:
                self.inserv._restart(dev_name)
            except Exception as exc:
                print(f'Failed to restart device "{dev_name}"')
                return

    def do_restart_all(self, arg_string: str):
        """Restart all devices"""
        if arg_string:
            print('Expected 0 args')
            return
        try:
            for name in list(self.inserv._devices.keys()):
                self.inserv._restart(name)
        except Exception as exc:
            print(f'Failed to restart all devices')
            return

    def do_EOF(self, _):
        """Stop the instrument server and exiting"""
        print("Stopping instrument server...")
        self.inserv.stop()
        return True