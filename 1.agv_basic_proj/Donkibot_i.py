import time
import serial

class Comm:
    def __init__(self, port, baudrate):
        self.ser = serial.Serial()
        self.ser.port = port
        self.ser.baudrate = baudrate
        self.ser.timeout = 0.1
        self.ser.open()
        if self.ser.is_open:
            print(f'serial port {port} is opened')
        else:
            print('serial port open error')
            raise Exception('serial port open error')
        
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()
        print('serial init complete')

    def CLR(self, vl: int, vr: int, LIMIT_SPEED: int = 100):

        try:
            send_vl = max(-LIMIT_SPEED, min(LIMIT_SPEED, int(vl)))
            send_vr = max(-LIMIT_SPEED, min(LIMIT_SPEED, int(vr)))
            
            if self.ser.writable():
                self.ser.write((f'$CLR,{send_vl},{send_vr}' + '\r\n').encode())
                print(f'Sent: $CLR,{send_vl},{send_vr}')
        except ValueError:
            print("Invalid vl or vr input")


if __name__ == '__main__':
    test = Comm( '/dev/ttyUSB0',115200)   #'/dev/ttyMCU', 115200)
    print("Entering main")
    try:
        while True:
            test.CLR(0, 100)
            time.sleep(0.01)
    except Exception as e:
        print(e)
    finally:
        test.ser.close()