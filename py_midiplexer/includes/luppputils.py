import json
import os
def genconfig():
    """
    Generates basic luppp config for use with pymidiplexer.
    """
    #luppp config dict
    lcd = {"name": "py-midiplexer",
           "author": os.environ["USER"]}
    
    input_bindings = []
    status_states = {176: 1, 0: 0}
    for track in range(1,10):
        for status, active_state in status_states.items():
            input_bindings.append({"action": "grid:event",
                                   "status": status,
                                   "track": track,
                                   "data": track,
                                   "scene": 0,
                                   "active": active_state})
            
                               
    lcd.update({"inputBindings": input_bindings})
    return json.dumps(lcd, indent=2)

if __name__ == "__main__":
    print(genconfig())

