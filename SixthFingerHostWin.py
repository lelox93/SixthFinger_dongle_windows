import socket
import serial
from serial.threaded import ReaderThread, Protocol
import threading
import time
from COMDeviceManager import COMDeviceManager  # Assicurati che il modulo sia nel PYTHONPATH

# Impostazioni UDP
UDP_IP = "127.0.0.1"
UDP_CMD_PORT = 5005       # Porta per ricevere i comandi (stato)
UDP_FEEDBACK_PORT = 5006  # Porta per inviare i dati (torque e position)

# Variabili globali per lo stato (equivalente al callback ROS)
current_state_string = ""
state_changed = False
state_lock = threading.Lock()

def udp_command_listener():
    """
    Thread che ascolta i comandi UDP su UDP_CMD_PORT.
    I messaggi attesi sono stringhe come "CLOSE", "STOP" o "OPEN".
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_CMD_PORT))
    print(f"Ascolto comandi UDP su {UDP_IP}:{UDP_CMD_PORT}")
    while True:
        try:
            data, addr = sock.recvfrom(1024)
            cmd = data.decode('utf-8').strip()
            with state_lock:
                global current_state_string, state_changed
                current_state_string = cmd
                state_changed = True
            print(f"Ricevuto comando UDP: {cmd}")
        except Exception as e:
            print("Errore nel listener UDP:", e)

def process_packet(packet, udp_sock):
    """
    Elabora un pacchetto (assunto lungo 11 byte, inizio con '$')
    ed estrae torque e position per poi inviarli via UDP.
    Formato atteso:
      index 0: '$'
      index 1-3: cifre del torque
      index 5-7: cifre della position
    """
    try:
        torque_val = ((packet[1] - ord('0')) * 100 +
                      (packet[2] - ord('0')) * 10 +
                      (packet[3] - ord('0')))
        # Legge il valore di position dagli indici 5,6,7
        position_val = ((packet[5] - ord('0')) * 100 +
                        (packet[6] - ord('0')) * 10 +
                        (packet[7] - ord('0')))
    except Exception as e:
        print("Errore nel processing del pacchetto:", e)
        return

    print(f"Torque: {torque_val} - Position: {position_val}")
    # Costruisce il messaggio includendo entrambi i valori
    message = f"{torque_val} {position_val}"
    try:
        udp_sock.sendto(message.encode(), (UDP_IP, UDP_FEEDBACK_PORT))
    except Exception as e:
        print("Errore nell'invio UDP:", e)

class SerialProtocol(Protocol):
    """
    Protocollo per ReaderThread che accumula i dati in un buffer.
    Quando trova un pacchetto completo (11 byte che iniziano con '$'),
    lo passa alla callback `packet_callback`.
    """
    def __init__(self, packet_callback, packet_length=11, start_byte=b'$'):
        self.packet_callback = packet_callback
        self.packet_length = packet_length
        self.start_byte = start_byte
        self.buffer = bytearray()

    def data_received(self, data):
        self.buffer.extend(data)
        while True:
            start_index = self.buffer.find(self.start_byte)
            if start_index == -1:
                if len(self.buffer) > 1024:
                    self.buffer.clear()
                break
            if len(self.buffer) < start_index + self.packet_length:
                break
            packet = self.buffer[start_index:start_index+self.packet_length]
            del self.buffer[:start_index+self.packet_length]
            self.packet_callback(packet)

def set_velocity_cmd(ser):
    """Invia il comando di velocità '$VS***' alla porta seriale."""
    data = b"$VS***"
    print("Invio comando di velocità:", data)
    try:
        ser.write(data)
    except Exception as e:
        print("Errore nell'invio del comando di velocità:", e)

def main():
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    dongle_type = "robot"  # Può essere "feedback", "input" o "robot"
    comport = COMDeviceManager.discover_com_devices(dongle_type)
    if not comport:
        print("Nessun dispositivo COM trovato per il dongle specificato.")
        return
    ser = COMDeviceManager.open_serial_port(comport)
    if ser is None:
        print("Apertura della porta seriale fallita.")
        return
    print("Porta seriale aperta correttamente:", comport)

    try:
        while ser.in_waiting:
            ser.read(ser.in_waiting)
    except Exception as e:
        print("Errore nel flush della porta seriale:", e)
    set_velocity_cmd(ser)

    udp_thread = threading.Thread(target=udp_command_listener, daemon=True)
    udp_thread.start()

    def packet_callback(packet):
        process_packet(packet, udp_sock)

    with ReaderThread(ser, lambda: SerialProtocol(packet_callback)) as protocol:
        loop_delay = 0.03  # 33 Hz ~ 30 ms per ciclo
        try:
            while True:
                cycle_start = time.perf_counter()
                global current_state_string, state_changed
                if state_changed:
                    with state_lock:
                        cmd = current_state_string
                        state_changed = False
                    data = bytearray(7)
                    data[0] = ord('$')
                    if cmd == "CLOSE":
                        data[1] = ord('C')
                    elif cmd == "STOP":
                        data[1] = ord('S')
                    elif cmd == "OPEN":
                        data[1] = ord('O')
                    else:
                        print("Comando sconosciuto ricevuto:", cmd)
                        continue
                    for i in range(2, 6):
                        data[i] = ord('*')
                    try:
                        ser.write(data[:-1])
                        print("Comando inviato al dongle:", data[:-1].decode('ascii', errors='ignore'))
                    except Exception as e:
                        print("Errore nell'invio del comando sulla porta seriale:", e)
                elapsed = time.perf_counter() - cycle_start
                remaining_time = loop_delay - elapsed
                if remaining_time > 0:
                    time.sleep(remaining_time)
        except KeyboardInterrupt:
            print("Terminazione tramite KeyboardInterrupt.")
        except Exception as e:
            print("Errore nel loop principale:", e)
        finally:
            udp_sock.close()
            print("Chiusura dell'endpoint UDP.")

if __name__ == "__main__":
    main()
