class PyMidiPlexerException(Exception):
    def __init__(self):
        self.msg = f"Error: {self.msg}"
        super().__init__()

class NoSuchTrack(PyMidiPlexerException):
    def __init__(self, client, track_label):
        self.track_label = track_label
        self.msg = f"No track matching label '{track_label}' for client '{client}'."
        print(self.msg)
        super().__init__()
        
class NoSuchSignal(PyMidiPlexerException):
    def __init__(self, controller, signal):
        self.msg = f"No signal matching label '{signal}' for controller '{controller}'."
        super().__init__()
        
class NothingToDo(PyMidiPlexerException):
    msg = "Nothing to do."
