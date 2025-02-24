#include <iostream>
#include <libudev.h>
#include <vector>
#include <algorithm>
#include <cstring>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>
#include <termios.h>
#include <chrono>
#include <thread>
#include <cstdlib>  // For system()
#include <sys/ioctl.h>
#include <errno.h>
#include <ros/ros.h>
#include <std_msgs/Int32.h> // Include necessary ROS message type
#include <smi_v1/test_feedback_msg.h>
#include <fstream>
#include <queue>
#include <mutex>
#include <condition_variable>

#include <std_msgs/String.h>
#include <sixthfinger_v1/TTYDeviceManager.h>
#include <smi_v1/pulsed_feedback_info.h>
#include <smi_v1/SCEN2_FINGER_state_machine.h>

SCEN2_FINGER_StateMachine state_machine;
bool state_changed = false;
std::string current_state_string;

void stateStringCallback(const std_msgs::String::ConstPtr& msg) {
    current_state_string = msg->data;
    state_changed = true; // Setta la flag di cambiamento di stato
}

// #include <iostream>

#define TARGET_VID "303a"
#define TARGET_PID "1001"



// Prototipo della funzione processBuffer
void processBuffer(const char* buffer, ros::Publisher& torque_pub, ros::Publisher& position_pub, int& torque_val, int& position_val);

// Prototipo della funzione setVelocityCMD
void setVelocityCMD(int serial_fd);

// Prototipo della funzione flushSerialPort
void flushSerialPort(int serial_fd);

// Function to map a value from one range to another
double map(double value, double fromLow, double fromHigh, double toLow, double toHigh) {
    return toLow + (value - fromLow) * (toHigh - toLow) / (fromHigh - fromLow);
}


int main(int argc, char** argv) {
    std::string dongle_type = "robot"; // Or "input" or "feedback"
    std::string devnode = TTYDeviceManager::discoverTTYDevices(dongle_type);
    if (!devnode.empty()) {
        std::cout << "Devnode associated with " << dongle_type << ": " << devnode << std::endl;
    } else {
        std::cout << "No device found for the specified dongle type." << std::endl;
    }

    

    // Initialize ROS node
    ros::init(argc, argv, "SCEN2_FINGER_event_driven_control");
    ros::NodeHandle nh;

    // Subscribe to the feedback topic
    ros::Subscriber state_sub = nh.subscribe("state_machine_state_string", 10, stateStringCallback);

    // Publisher setup
    ros::Publisher torque_pub = nh.advertise<std_msgs::Int32>("torque_info", 10); // 10 is the queue size
    ros::Publisher position_pub = nh.advertise<std_msgs::Int32>("position_info", 10); // 10 is the queue size




    int torque_val = 0;
    int position_val = 0;

     ROS_WARN("sixthfinger_node: WORKING");
        
    // Variabili globali per conservare l'ultimo buffer valido
    char last_valid_buffer[13] = {0}; // Inizializza con terminatori nulli
    bool buffer_valid = false;

    ros::Time time_init;
    ros::Duration time_vibration = ros::Duration(0.5);

    // Open serial port and configure
    int serial_fd = TTYDeviceManager::openSerialPort(devnode);
    if (serial_fd == -1) {
        return EXIT_FAILURE;
    }
    printf("Serial port opened and configured successfully\n\n");

    // Set loop rate
    ros::Rate loop_rate(33.33); // 50Hz

    char buffer[13]; // Buffer per i dati letti, dimensione 12+1 per il terminatore nullo
    char start_byte = '$'; // Byte di inizio atteso
    bool start_byte_found_flag = false;
    int bytes_available = 0;

    // Esegui il flush dei byte disponibili prima di iniziare a leggere
    flushSerialPort(serial_fd);

    // Setta la velocità a bassa
    setVelocityCMD(serial_fd);

    // Write to serial port continuously
    while (ros::ok()) {


        if (state_changed) {
            std::cout << "DAJE MPO" << std::endl;
            char data[7];
            // React based on the received state string
            if (current_state_string == "CLOSE") {
                // Perform actions for CLOSE state
                data[0] = '$';
                data[1] = 'C';
            } else if (current_state_string == "STOP") {
                // Perform actions for STOP state
                data[0] = '$';
                data[1] = 'S';
            } else if (current_state_string == "OPEN") {
                // Perform actions for OPEN state
                data[0] = '$';
                data[1] = 'O';
            } else {
                ROS_WARN("Received unknown state: %s", current_state_string.c_str());
            }

            data[2] = '*';
            data[3] = '*';
            data[4] = '*';
            data[5] = '*';
            data[6] = '\0'; //FONDAMENTALE

            // Usa ROS_INFO per stampare i dati
            ROS_WARN("Data to send: %s", data);

            write(serial_fd, data, strlen(data));
            state_changed = false; // Resetta la flag di cambiamento di stato
        }




        ioctl(serial_fd, FIONREAD, &bytes_available);
        // ROS_WARN("Bytes_Ava: %d", bytes_available); // Stampa con ROS_WARN

        if (bytes_available > 0) {

            // Scarta i byte fino a trovare un nuovo pacchetto valido
            while (bytes_available > 0) {
                read(serial_fd, &buffer[0], 1);
                if (buffer[0] == start_byte) {
                    start_byte_found_flag = true;
                    break;
                }
                ioctl(serial_fd, FIONREAD, &bytes_available);
            }

            if (bytes_available >= 10) {
                read(serial_fd, &buffer[1], 10);
                start_byte_found_flag = false;

                // Conserva l'ultimo buffer valido
                std::memcpy(last_valid_buffer, buffer, 12);
                buffer_valid = true;

                // Stampa il buffer
                std::cout << buffer << std::endl;
                std::cout << "--------------------" << std::endl;

                // Processa il buffer
                processBuffer(buffer, torque_pub, position_pub, torque_val, position_val);
            } else {
                if (buffer_valid) {
                    // Usa l'ultimo buffer valido per la conversione
                    processBuffer(buffer, torque_pub, position_pub, torque_val, position_val);
                }
            }
            
        }

        loop_rate.sleep(); // Control loop frequency
        ros::spinOnce(); // Allow ROS to process callback
    }

    // Close serial port
    close(serial_fd);
    printf("Serial port closed\n");

    return EXIT_SUCCESS;
}


















void processBuffer(const char* buffer, ros::Publisher& torque_pub, ros::Publisher& position_pub, int& torque_val, int& position_val) {
    // Estrazione e conversione dei primi 3 caratteri del buffer in un valore intero
    int digit1 = buffer[1] - '0';
    int digit2 = buffer[2] - '0';
    int digit3 = buffer[3] - '0';
    torque_val = digit1 * 100 + digit2 * 10 + digit3;

    // Estrazione e conversione dei caratteri dal sesto all'ottavo del buffer in un valore intero
    int digit6 = buffer[6] - '0';
    int digit7 = buffer[7] - '0';
    int digit8 = buffer[8] - '0';
    position_val = digit6 * 100 + digit7 * 10 + digit8;

    // Pubblica i valori sui topic ROS
    std_msgs::Int32 msg_t;
    msg_t.data = torque_val;
    torque_pub.publish(msg_t);

    std_msgs::Int32 msg_p;
    msg_p.data = position_val;
    position_pub.publish(msg_p);
}


// Funzione per fare il flush dei byte disponibili sulla porta seriale
void flushSerialPort(int serial_fd) {
    int bytes_available = 0;
    ioctl(serial_fd, FIONREAD, &bytes_available);
    while (bytes_available > 0) {
        char flush_buffer[512]; // Buffer temporaneo per leggere i byte disponibili
        int bytes_to_read = std::min(bytes_available, static_cast<int>(sizeof(flush_buffer)));
        read(serial_fd, flush_buffer, bytes_to_read);
        ioctl(serial_fd, FIONREAD, &bytes_available);
    }
}


void setVelocityCMD(int serial_fd){
        char data[7];
        data[0] = '$';
        data[1] = 'V';
        data[2] = 'S';
        data[3] = '*';
        data[4] = '*';    
        data[5] = '*';    
        data[6] = '\0'; //FONDAMENTALE

        // Usa ROS_INFO per stampare i dati
        ROS_WARN("Data to send: %s", data);

        write(serial_fd, data, strlen(data));
}