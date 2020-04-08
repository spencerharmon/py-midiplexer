import logging
class Track(object):
    """
    Generic track superclass.
    """
    def __init__(self, label):
        self.label = label
        #always initiate to false?
        self.playing=False
        self.logger = logging.getLogger(f'{__class__.__name__}:{str(self.label)}')

    def trigger(self, port):
        pass

    def is_playing(self):
        return self.playing
    
    def __dict__(self):
        return {self.number: {"midi_data": self.midi_data, "midi_value": self.midi_value}}

import mido

class MidiTrack(Track):
    def __init__(self, label, attrs):
        super().__init__(label)
        self.attr_dict = attrs['data']
        self.typ = attrs['type']
        self.msg = self.get_msg()

    def get_msg(self) -> mido.Message:
        """
        parse the msg_dict and return a mido Message.
        validation is performed by the mido Message class.
        """

        try:
            channel = self.attr_dict['channel']
        except KeyError:
            channel = 0

        try:
            note = self.attr_dict['note']
        except KeyError:
            note = 0

        try:
            velocity = self.attr_dict['velocity']
        except KeyError:
            velocity = 64

        try:
            value = self.attr_dict['value']
        except KeyError:
            value = 0

        try:
            control = self.attr_dict['control']
        except KeyError:
            control = 0

        try:
            program = self.attr_dict['program']
        except KeyError:
            program = 0

        try:
            pitch = self.attr_dict['pitch']
        except KeyError:
            pitch = 0

        try:
            data = self.attr_dict['data']
        except KeyError:
            data = 0

        try:
            frame_type = self.attr_dict['frame_type']
        except KeyError:
            frame_type = 0

        try:
            frame_value = self.attr_dict['frame_value']
        except KeyError:
            frame_value = 0

        try:
            pos = self.attr_dict['pos']
        except KeyError:
            pos = 0

        try:
            song = self.attr_dict['song']
        except KeyError:
            song = 0
            
        if self.typ == "note_off":
            return mido.Message(self.typ, channel=channel, note=note, velocity=velocity)
        elif self.typ == "note_on":
            return mido.Message(self.typ, channel=channel, note=note, velocity=velocity)
        elif self.typ == "polytouch":
            return mido.Message(self.typ, channel=channel, note=note, value=value)
        elif self.typ == "control_change":
            return mido.Message(self.typ, channel=channel, control=control, value=value)
        elif self.typ == "program_change":
            return mido.Message(self.typ, channel=channel, program=program)
        elif self.typ == "aftertouch":
            return mido.Message(self.typ, channel=channel, value=value)
        elif self.typ == "pitchwheel":
            return mido.Message(self.typ, channel=channel, pitch=pitch)
        elif self.typ == "sysex":
            return mido.Message(self.typ, data=data)
        elif self.typ == "quarter_frame":
            return mido.Message(self.typ, frame_type=frame_type, frame_value=frame_value)
        elif self.typ == "songpos":
            return mido.Message(self.typ, pos=pos)
        elif self.typ == "song_select":
            return mido.Message(self.typ, song=song)
        elif self.typ == "tune_request":
            return mido.Message(self.typ)
        elif self.typ == "clock":
            return mido.Message(self.typ)
        elif self.typ == "start":
            return mido.Message(self.typ)
        elif self.typ == "continue":
            return mido.Message(self.typ)
        elif self.typ == "stop":
            return mido.Message(self.typ)
        elif self.typ == "reset":
            return mido.Message(self.typ)

    def trigger(self, port, desired_state):
        the_same = self.playing
        if desired_state is None:
            #trigger mode
            if self.playing:
                self.playing=False
            else:
                self.playing=True
            port.send(self.msg)
            
        elif desired_state:
            #desired playing
            if not self.playing:
                port.send(self.msg)
                self.playing = True
        else:
            # desired stopped
            if self.playing:
                port.send(self.msg)
                self.playing = False
                
        if self.playing is not the_same:
            m = {False: "not playing",
                 True: "playing"}
            self.logger.debug(f'State changed from {m[the_same]} to {m[self.playing]}.')

    def get_config_dict(self):
        return {"label": self.label, "type": self.typ, "data": self.attr_dict}
