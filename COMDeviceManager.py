import serial
from serial.tools import list_ports

class COMDeviceManager:
    @staticmethod
    def is_in_list(serial_number, serial_list):
        """Verifica se il numero di serie è presente nella lista."""
        return serial_number in serial_list

    @staticmethod
    def open_serial_port(comport):
        """
        Apre la porta seriale con le impostazioni:
          - Baudrate: 115200
          - 8 bit, nessuna parità, 1 bit di stop
          - Nessun controllo hardware/software
        """
        try:
            ser = serial.Serial(comport, baudrate=115200, timeout=0.1)
        except Exception as e:
            print(f"Errore nell'apertura della porta COM {comport}: {e}")
            return None

        # Impostazioni aggiuntive (pyserial imposta per default 8N1, ma le esplicitiamo)
        ser.bytesize = serial.EIGHTBITS
        ser.parity = serial.PARITY_NONE
        ser.stopbits = serial.STOPBITS_ONE
        ser.timeout = 0.1
        ser.xonxoff = False
        ser.rtscts = False
        ser.dsrdtr = False
        return ser

    @staticmethod
    def discover_com_devices(dongle_type):
        """
        Cerca porte COM e restituisce la porta associata al tipo di dongle richiesto.
        I tipi ammessi sono "feedback", "input" o "robot". Le liste dei numeri di serie sono
        hard-coded come nell'implementazione C++.
        """
        comport_associated = ""

        # Liste di numeri di serie per ciascun tipo
        feedback = ["EC:DA:3B:5D:28:B4", "EC:DA:3B:5D:28:B5", "EC:DA:3B:5D:28:B6"]
        input_list = ["EC:DA:3B:5D:27:33", "EC:DA:3B:5D:27:31", "EC:DA:3B:5D:27:32"]
        robot = ["EC:DA:3B:5B:6C:00", "EC:DA:3B:5D:27:30", "EC:DA:3B:5D:27:35", "DC:DA:0C:30:C2:74"]

        # Usa serial.tools.list_ports per Windows
        ports = list_ports.comports()
        for port in ports:
            comport = port.device
            serial_number = getattr(port, 'serial_number', None)
            if not serial_number:
                continue
            print(f"HARIA device found: {serial_number} at COM Port: {comport}")
            if dongle_type == "feedback" and COMDeviceManager.is_in_list(serial_number, feedback):
                comport_associated = comport
                break
            elif dongle_type == "input" and COMDeviceManager.is_in_list(serial_number, input_list):
                comport_associated = comport
                break
            elif dongle_type == "robot" and COMDeviceManager.is_in_list(serial_number, robot):
                comport_associated = comport
                break

        return comport_associated


# Esempio di utilizzo
if __name__ == "__main__":
    dongle_type = "robot"  # Può essere "feedback", "input" o "robot"
    comport = COMDeviceManager.discover_com_devices(dongle_type)
    if comport:
        print(f"Porta COM associata a {dongle_type}: {comport}")
        ser = COMDeviceManager.open_serial_port(comport)
        if ser:
            print("Porta seriale aperta con successo!")
            # Qui potresti procedere con la lettura/scrittura sulla porta...
            ser.close()
        else:
            print("Apertura della porta seriale fallita.")
    else:
        print("Nessun dispositivo trovato per il dongle specificato.")
