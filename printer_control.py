import serial
from serial.tools import list_ports
import time
import sys
import keyboard

# --- Configuration ---
BAUDRATES = [9600, 115200]
LIMITS = {'X': 220, 'Y': 220, 'Z': 150}
OUT_Y=0
OUT_X=30
OUT_Z=5
STEP_SIZE = 10 

class PrinterController:
    rellay_mode=1
    def __init__(self):
        self.current_pos = {'X': 0.0, 'Y': 0.0, 'Z': 0.0}
        self.is_busy = False 

        self.rellay_mode=1
        self.main_init()
        

    def rellay_connect(self):
        try:
            self.rellay_ser = serial.Serial(self.rellay_port, BAUDRATES[0], timeout=1)
            time.sleep(2) 
            print(f"Connected to rellay on {self.rellay_port}")
        except Exception as e:
            print(f"Connection failed: {e}")
            sys.exit()

    def printer_connect(self):
        try:
            self.ser = serial.Serial(self.printter_port, BAUDRATES[1], timeout=1)
            time.sleep(2) 
            print(f"Connected to printer on {self.printter_port}")
        except Exception as e:
            print(f"Connection failed: {e}")
            sys.exit()

    def main_init(self):
        self.printter_port=None
        self.rellay_port=None
        devices_ports=self.find_right_device()
        if devices_ports[0]!=None:
            self.printter_port=devices_ports[0]
        if devices_ports[1]!=None:
            self.rellay_port=devices_ports[1]
       
        self.printer_connect()

        self.rellay_connect()
        
        self.initialize()

    def hard_reset_state(self):
        self.rellay_close()
        self.printer_close()
        time.sleep(2)
        self.main_init()

    def find_right_device(self):
        printer_port=None
        rellay_port=None
        for port in list_ports.comports():
            for baud in BAUDRATES:
                try:
                    ser = serial.Serial(port.device, baudrate=baud, timeout=1)

                    # example probe command
                    ser.write(b'ID?\r\n')
                    reply = ser.readline()
                    if reply !=b'':
                        if baud==9600:
                            rellay_port=port.device
                        if baud==115200:
                            printer_port=port.device
                    print(port.device, baud, reply)

                    ser.close()
                    
                except Exception as e:
                    print(port.device, baud, e)
        return (printer_port,rellay_port)

    #rellay part
    def send_command(self, target, action):
        try:
            cmd = bytes([0xFF, 0xFF, target, action])
            self.rellay_ser.write(cmd)
            time.sleep(0.05)
        except Exception as e:
            print(f"Relay Serial Error: {e}. Attempting to reconnect...")
            try:
                self.rellay_ser.close()
                # You might need to re-find the port here as it often changes /dev/ttyUSB index
                self.rellay_connect() 
            except:
                print("Critical: Could not recover relay connection.")
        # cmd = bytes([0xFF, 0xFF, target, action])
        # self.rellay_ser.write(cmd)
        # time.sleep(0.05)

    def read_response(self):
        # Expect 4 bytes: FF FF XX 0A
        resp = self.rellay_ser.read(4)
        if len(resp) != 4:
            raise RuntimeError(f"Incomplete response: {resp}")
        if resp[0] != 0xFF or resp[1] != 0xFF or resp[3] != 0x0A:
            raise RuntimeError(f"Invalid response: {resp}")
        return resp

    def get_status_raw(self):
        # Send status request: FF FF AA 03
        self.rellay_ser.write(bytes([0xFF, 0xFF, 0xAA, 0x03]))
        time.sleep(0.05)
        resp = self.read_response()
        return resp[2]  # XX byte (bitmask)

    def get_status(self):
        status_byte = self.get_status_raw()
        return {
            "relay1": bool(status_byte & 0b00000001),
            "relay2": bool(status_byte & 0b00000010),
        }

    def is_relay_on(self, relay_number):
        status_byte = self.get_status_raw()
        bit = relay_number - 1
        return bool(status_byte & (1 << bit))

    # --- control functions ---
    def all_off(self):
        self.send_command(0xAA, 0x00)

    def relay1_on_relay2_off(self):
        self.all_off()
        self.send_command(0x01, 0x01)
        self.send_command(0x02, 0x00)

    def relay2_on_relay1_off(self):
        self.all_off()
        self.send_command(0x01, 0x00)
        self.send_command(0x02, 0x01)

    def set_state(self, value):
        # bitmask control (A1 mode)
        self.send_command(0xA1, value)

    def rellay_close(self):
        self.rellay_ser.close()

    #printer part


    def printer_close(self):
        self.ser.close()

    def send_gcode(self, code):
        """Sends G-code and blocks until 'ok' is received."""
        if not code: return
        self.ser.write(f"{code}\n".encode())
        while True:
            line = self.ser.readline().decode().strip()
            if "ok" in line.lower():
                break

    def move(self, axis, distance):
        if self.is_busy: return
        
        new_pos = self.current_pos[axis] + distance
        if 0 <= new_pos <= LIMITS[axis]:
            self.current_pos[axis] = new_pos
            #print(f"G1 {axis}{round(new_pos, 2)} F3000")
            self.send_gcode(f"G1 {axis}{round(new_pos, 2)} F3000")
        else:
            print(f"Boundary Alert: {axis} limit reached.")

    def initialize(self):
        self.current_pos = {'X': 0.0, 'Y': 0.0, 'Z': 0.0}
        self.is_busy = False
        self.all_off()
        self.is_busy = True
        print("System Start: Homing and moving to Z-Max...")
        self.send_gcode("G90") # Absolute
        self.send_gcode("G28") # Home
        self.send_gcode(f"G1 Z{LIMITS['Z']} F6000")
        self.send_gcode("M400")
        self.current_pos = {'X':0.0, 'Y': LIMITS['Y'], 'Z': LIMITS['Z']}
        print("Ready.")
        self.is_busy = False

    def special_sequence_5(self):
        self.custom_function()
        self.is_busy = True
        print("Routine 5: Moving to Z30...")
        half_z=LIMITS['Z']/2
        # 1. Move to Z 20mm
        self.send_gcode(f"G1 Z{OUT_Z} F3000")
        self.send_gcode("M400")
        self.current_pos['Z'] = OUT_Z
        self.send_gcode(f"G1 Z{half_z} F3000")
        self.send_gcode("M400")
        self.current_pos['Z'] = half_z
        # 3. Move Bed to Max Y
        print(f"Moving Bed to Y{OUT_Y}...")
        self.send_gcode(f"G1 Y{OUT_Y} F6000")
        self.send_gcode("M400")
        self.current_pos['Y'] = OUT_Y
        self.send_gcode(f"G1 X{OUT_X} F6000")
        self.send_gcode("M400")
        self.current_pos['X'] = OUT_X
        self.all_off()
        time.sleep(0.5)
        print("Routine 5 Finished.")
        self.is_busy = False

    def custom_function(self):
        if self.rellay_mode==1:
            self.relay1_on_relay2_off()
        else:
            self.relay2_on_relay1_off()
        print(">>> Triggering custom logic at Z=20mm...")
        time.sleep(1)

    def run(self):
        print("Script running. Press '-' to exit.")
        
        while True:
            if keyboard.is_pressed('.'):
                self.hard_reset_state()

            if self.is_busy:
                if keyboard.is_pressed('7'):
                    self.initialize()
                time.sleep(0.1)
                continue

            # Movement logic with reversed Y
            if keyboard.is_pressed('8'):
                self.move('Y', -STEP_SIZE)
            elif keyboard.is_pressed('2'):
                self.move('Y', STEP_SIZE)
            elif keyboard.is_pressed('4'):
                self.move('X', -STEP_SIZE)
            elif keyboard.is_pressed('6'):
                self.move('X', STEP_SIZE)
            
            # Action keys
            elif keyboard.is_pressed('7'):
                self.initialize()
            elif keyboard.is_pressed('5'):
                self.special_sequence_5()
            elif keyboard.is_pressed('3'):
                self.custom_function()
            elif keyboard.is_pressed('0'):
                self.all_off()
            elif keyboard.is_pressed('1'):
                if self.rellay_mode==1:
                    self.rellay_mode=2
                else:
                    self.rellay_mode=1
            elif keyboard.is_pressed('9'):
                self.rellay_close()
                self.printer_close()
                print("Exiting...")
                break
            
            time.sleep(0.1) # Prevents CPU over-usage



if __name__ == "__main__":
    controller = PrinterController()
    controller.run()
