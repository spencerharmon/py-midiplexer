import multiprocessing
import queue
import logging
import time

class Controller(multiprocessing.Process):
    """
    Generic controller superclass. Only midi is implemented for now, but who knows? Maybe there will be something else.
    All controllers can register new signal mappings, and modify or delete existing ones.
    Subclasses will establish their communication mechanism, e.g. jack midi, osc, REST, et c. and therefore will define the
    behavior for the listen method.
    All controllers have a name and a signal list. The signal's list index should be returned when a signal is 
    """
    def __init__(self, shutdown_callback, signal_queue, stdout_queue, name: str, signal_map: dict={}):
        self.signal_queue = signal_queue
        self.stdout_queue = stdout_queue
        self.command_queue = multiprocessing.Queue()
        self.config_queue = multiprocessing.Queue()
        self.shutdown_callback = shutdown_callback
        self.check_lock = multiprocessing.Lock()
        self.type = None
        self.signal_map = signal_map
        super().__init__()
        self.name = name
        self.logger = logging.getLogger(f'{self.__class__.__name__}:{self.name}')

    def listen(self):
        """
        listen for incoming signals. Subclasses must override and return the list index from self.signal_list if a valid
        signal is detected.
        """
        return 0

    def check(self):
        return 0
    
    def register(self):
        pass

    def run(self):
        pass
    
    def shutdown(self):
        try:
            self.port.close()
        except:
            pass
        self.command_queue.close()
        self.logger.info(f"Exiting.")
        
    def queue_config_dict(self):
        self.config_queue.put({"name": self.name, "type": self.type, "signal_map": self.signal_map})


class MidiController(Controller):
    def __init__(self,
                 shutdown_callback,
                 signal_queue,
                 stdout_queue,
                 name: str,
                 signal_map: dict={},
                 backend='mido.backends.rtmidi/UNIX_JACK'):
        super().__init__(shutdown_callback, signal_queue, stdout_queue, name, signal_map)
        self.type="midi"
        self.backend = backend

    def listen(self):
        """
        Listens continuously for a midi signal and returns a label once one is received.
        Deprecated.
        """
        while True:
            msg = self.port.receive()
            try:
                return self.signal_map[msg.hex()]
            except KeyError:
                continue

    def check(self):
        """
        returns a signal label if a signal was received, or None otherwise.
        """
        time.sleep(0.008) #rate-limit polling. just a little faster than midi..
        self.check_lock.acquire()
        msg = self.port.poll()
        self.check_lock.release()

        if msg is None:
            return None
        else:
            try:
                signal = self.signal_map[msg.hex()]
                self.logger.info(f'Received midi message "{msg.hex()}"; sending signal {signal}.')
                return self.signal_map[msg.hex()]
            except KeyError:
                self.logger.debug(f'Received midi message "{msg.hex()}". No entry in signal map.')
                return None
    

    def register(self, signal=None):
        if signal is None:
            signal = len(self.signal_map)
        self.logger.warn(f'Pausing input to register signal {signal}.')
        self.check_lock.acquire()
        msg = self.port.receive()
        self.check_lock.release()
        self.logger.info(f'Registered midi signal "{msg.hex()}" with label {signal}.')
        self.signal_map.update({msg.hex(): signal})

    def process_commands(self):
        """
        Commands are passed to the controller daemon proccess by the PyMidiPlexer class after receiving events from the 
        Cli (future api server? midi meta-controller? who knows?) via the command queue processed my this method.
        All commands in the queue are processed before polling for midi signals by the run thread can resume.
        """
        while True: #eh? always process all the commands? Careful. This blocks signals.
            try:
                command = self.command_queue.get_nowait()
                self.logger.debug(f"Received command {command}.")
                for c, args in command.items():
                    if c == 'register':
                        self.register(args)
                    if c == 'queue_config_dict':
                        self.queue_config_dict()
                if self.command_queue.empty():
                    break
            except queue.Empty:
                break
    def process_signals(self):
        signal = self.check()
        if signal is not None:
            self.signal_queue.put((self.name, signal))
        
    def run(self):
        """
        This is the entry point for the controller when running in daemon mode.
        """
        #late import. make sure everything related to the port is in this process.
        import mido

        mido.set_backend(self.backend)
        self.port = mido.open_input(self.name, client_name="py_midiplexer", virtual=True)
        self.logger.debug(f"Starting.")
        while not self.shutdown_callback.is_set():
            self.process_commands()
            self.process_signals()
        # after shutdown callback is set.
        self.shutdown()
