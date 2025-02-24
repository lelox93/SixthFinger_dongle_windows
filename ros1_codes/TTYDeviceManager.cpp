// #include "sixthfinger_v1/include/sixthfinger_v1/TTYDeviceManager.h"
// #include "TTYDeviceManager.h"
#include <sixthfinger_v1/TTYDeviceManager.h>

bool TTYDeviceManager::isInList(const std::string& serial, const std::vector<std::string>& serialList) {
    return std::find(serialList.begin(), serialList.end(), serial) != serialList.end();
}

int TTYDeviceManager::openSerialPort(const std::string& devnode) {
    int serial_fd = open(devnode.c_str(), O_RDWR | O_NOCTTY | O_NDELAY);
    if (serial_fd == -1) {
        if(devnode.empty()){
            std::cout << "No Haria devices, closing." << std::endl;
            return -1;
        } else {
            fprintf(stderr, "Failed to open serial port %s\n", devnode.c_str());
            std::cout << "Give permission to the tty device or insert password: \n";
            sleep(1);
            std::string exe_str = "sudo chmod a+rw " + devnode;
            system(exe_str.c_str());
            serial_fd = open(devnode.c_str(), O_RDWR | O_NOCTTY | O_NDELAY);
        }
    }

    struct termios tty;
    memset(&tty, 0, sizeof(tty));

    if (tcgetattr(serial_fd, &tty) != 0) {
        fprintf(stderr, "Error %d from tcgetattr\n", errno);
        close(serial_fd);
        return -1;
    }

    cfsetospeed(&tty, B115200);
    cfsetispeed(&tty, B115200);

    tty.c_cflag &= ~PARENB; // No parity
    tty.c_cflag &= ~CSTOPB; // 1 stop bit
    tty.c_cflag &= ~CSIZE;
    tty.c_cflag |= CS8; // 8 bits per byte
    tty.c_cflag &= ~CRTSCTS; // No hardware flow control
    tty.c_cflag |= CREAD | CLOCAL; // Enable receiver, ignore control lines

    tty.c_iflag &= ~(IXON | IXOFF | IXANY); // Disable software flow control

    tty.c_lflag = 0; // No canonical mode
    tty.c_oflag = 0; // No output processing

    if (tcsetattr(serial_fd, TCSANOW, &tty) != 0) {
        fprintf(stderr, "Error %d from tcsetattr\n", errno);
        close(serial_fd);
        return -1;
    }

    return serial_fd;
}

std::string TTYDeviceManager::discoverTTYDevices(const std::string& dongle_type) {
    std::string devnode_associated;
    std::cout << "\n\n\t\t\t\033[1m\033[38;2;255;128;0m\033[48;2;0;0;255m   HARIA DONGLE MANAGER   \033[0m" << std::endl;

    // Create a udev context
    struct udev *udev = udev_new();
    if (!udev) {
        std::cerr << "Failed to create udev context" << std::endl;
        return devnode_associated;
    }

    // Create a udev enumerator
    struct udev_enumerate *enumerate = udev_enumerate_new(udev);
    if (!enumerate) {
        std::cerr << "Failed to create udev enumerator" << std::endl;
        udev_unref(udev);
        return devnode_associated;
    }

    // Set the subsystem filter to "tty"
    udev_enumerate_add_match_subsystem(enumerate, "tty");

    // Scan the devices
    udev_enumerate_scan_devices(enumerate);

    // Get a list of devices
    struct udev_list_entry *devices = udev_enumerate_get_list_entry(enumerate);

    // Iterate over the devices
    struct udev_list_entry *entry;
    udev_list_entry_foreach(entry, devices) {
        const char *path = udev_list_entry_get_name(entry);
        struct udev_device *dev = udev_device_new_from_syspath(udev, path);
        const char *devnode = udev_device_get_devnode(dev);
        if (devnode) {
            const char *vendor_id = udev_device_get_property_value(dev, "ID_VENDOR_ID");
            const char *product_id = udev_device_get_property_value(dev, "ID_MODEL_ID");
            const char *serial_number = udev_device_get_property_value(dev, "ID_SERIAL_SHORT");

            if (vendor_id && product_id) {
                std::cout << "\033[1m\033[38;2;0;128;255mHARIA device found:\t\033[0m";

                // Assuming dongle_type is a string passed to the function
                if (!dongle_type.empty() && serial_number) {
                    std::vector<std::string> feedback = {"EC:DA:3B:5D:28:B4", "EC:DA:3B:5D:28:B5", "EC:DA:3B:5D:28:B6"};
                    std::vector<std::string> input = {"EC:DA:3B:5D:27:33", "EC:DA:3B:5D:27:31", "EC:DA:3B:5D:27:32"};
                    std::vector<std::string> robot = {"EC:DA:3B:5B:6C:00", "EC:DA:3B:5D:27:30", "EC:DA:3B:5D:27:35"};

                    if (TTYDeviceManager::isInList(serial_number, feedback)) {
                        std::cout << "\033[1m\033[38;2;255;128;0mfeedback\033[0m \u2192 " << serial_number << " at TTY Port: " << devnode << std::endl;
                        if (dongle_type == "feedback")
                            devnode_associated = devnode;
                    } else if (TTYDeviceManager::isInList(serial_number, input)) {
                        std::cout << "   \033[1m\033[38;2;255;128;0minput\033[0m \u2192 " << serial_number << " at TTY Port: " << devnode << std::endl;
                        if (dongle_type == "input")
                            devnode_associated = devnode;
                    } else if (TTYDeviceManager::isInList(serial_number, robot)) {
                        std::cout << "   \033[1m\033[38;2;255;128;0mrobot\033[0m \u2192 " << serial_number << " at TTY Port: " << devnode << std::endl;
                        if (dongle_type == "robot")
                            devnode_associated = devnode;
                    }
                }
            }
            udev_device_unref(dev);
        }
    }

    // Cleanup
    udev_enumerate_unref(enumerate);
    udev_unref(udev);

    return devnode_associated;
}
