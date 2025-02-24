import socket
import serial
import threading
import time
from COMDeviceManager import COMDeviceManager  # Assicurati che COMDeviceManager.py sia nel PYTHONPATH

# Impostazioni UDP
UDP_IP = "127.0.0.1"
UDP_CMD_PORT = 5005       # Porta per ricevere i comandi (stato)
UDP_FEEDBACK_PORT = 5006  # Porta per inviare i dati (torque e position)

# Variabili globali per lo stato (equivalente al callback ROS)
current_state_string = ""
state_changed = False
state_lock = threading.Lock()

# Variabili per la gestione del buffer seriale
last_valid_buffer = b'\0' * 12
buffer_valid = False

def udp_command_listener():
    """
    Thread che ascolta i comandi UDP su UDP_CMD_PORT.
    I messaggi attesi sono stringhe come "CLOSE", "STOP" o "OPEN".
    """
    global current_state_string, state_changed
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_CMD_PORT))
    print(f"Ascolto comandi UDP su {UDP_IP}:{UDP_CMD_PORT}")
    while True:
        data, addr = sock.recvfrom(1024)
        cmd = data.decode('utf-8').strip()
        with state_lock:
            current_state_string = cmd
            state_changed = True
        print(f"Ricevuto comando UDP: {cmd}")

def process_buffer(buffer, udp_sock):
    """
    Estrae torque e position dal buffer e invia i valori tramite UDP.
    Il buffer è atteso nel formato: 
      index 0: '$'
      index 1-3: cifre del torque
      index 6-8: cifre della position
    """
    try:
        torque_val = ((buffer[1] - ord('0')) * 100 +
                      (buffer[2] - ord('0')) * 10 +
                      (buffer[3] - ord('0')))
        position_val = ((buffer[6] - ord('0')) * 100 +
                        (buffer[7] - ord('0')) * 10 +
                        (buffer[8] - ord('0')))
    except Exception as e:
        print("Errore nel processing del buffer:", e)
        return

    # Invia i valori via UDP (qui li inviamo separatamente; puoi combinare i messaggi se preferisci)
    msg_torque = f"{torque_val}"
    msg_position = f"{position_val}"
    udp_sock.sendto(msg_torque.encode('utf-8'), (UDP_IP, UDP_FEEDBACK_PORT))
    print(f"Torque: {torque_val} - Position: {position_val}")

def flush_serial_port(ser):
    """ Esegue il flush della porta seriale leggendo e scartando i byte disponibili """
    while ser.in_waiting:
        ser.read(ser.in_waiting)

def set_velocity_cmd(ser):
    """ Invia il comando di velocità "$VS***" alla porta seriale """
    data = b"$VS***"
    print("Invio comando di velocità:", data)
    ser.write(data)

def main():
    global state_changed, current_state_string, last_valid_buffer, buffer_valid

    # Imposta il socket UDP per l'invio dei feedback
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Utilizza COMDeviceManager per cercare la porta COM associata al dongle "robot"
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

    # Flush iniziale e invio comando di velocità
    flush_serial_port(ser)
    set_velocity_cmd(ser)

    # Avvia il thread per ricevere comandi UDP
    udp_thread = threading.Thread(target=udp_command_listener, daemon=True)
    udp_thread.start()

    loop_delay = 0.03  # Loop ~33 Hz

    while True:
        # Se è cambiato lo stato (ricevuto via UDP), invia il comando corrispondente al dongle
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
            # Simula un terminatore nullo non inviato (invia data[0]..data[5])
            ser.write(data[:-1])
            print("Comando inviato al dongle:", data[:-1].decode('ascii', errors='ignore'))

        # Gestione della lettura dalla porta seriale
        if ser.in_waiting > 0:
            # Cerca il byte di inizio '$'
            start_byte_found = False
            while ser.in_waiting:
                byte = ser.read(1)
                if byte == b'$':
                    start_byte_found = True
                    buffer = bytearray(b'$')
                    break
            if start_byte_found:
                # Attendi 10 byte aggiuntivi
                if ser.in_waiting >= 10:
                    data = ser.read(10)
                    buffer.extend(data)
                    last_valid_buffer = bytes(buffer)
                    buffer_valid = True
                    print("Ricevuto buffer:", buffer)
                    process_buffer(buffer, udp_sock)
                else:
                    # Se non ci sono abbastanza byte, usa l'ultimo buffer valido
                    if buffer_valid:
                        process_buffer(last_valid_buffer, udp_sock)

        time.sleep(loop_delay)

    ser.close()
    print("Porta seriale chiusa.")

if __name__ == "__main__":
    main()
