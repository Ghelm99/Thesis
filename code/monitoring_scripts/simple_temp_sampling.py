import os
import sys
import signal
import time
import threading
import matplotlib.pyplot as plt

stop_collection = False
sample_count = 0
count_lock = threading.Lock()

################################################################

def is_intel_cpu():
    try:
        with open("/proc/cpuinfo", "r") as f:
            return "GenuineIntel" in f.read()
    except Exception as e:
        print(f"Error checking CPU type: {e}")
        return False

################################################################

def look_for_right_path():
    print("Checking CPU type...")
    if is_intel_cpu():
        print("Intel CPU detected.")
    else:
        print("AMD CPU detected.")

    print("Looking for temp sensors...")
    hwmon_dir = "/sys/class/hwmon"

    for hwmon in os.listdir(hwmon_dir):
        hwmon_path = os.path.join(hwmon_dir, hwmon)
        try:
            for file in os.listdir(hwmon_path):
                if file.endswith("_label"):
                    label_file = os.path.join(hwmon_path, file)
                    with open(label_file, "r") as f:
                        label = f.read().strip()
                        print(f"Found label: {label} in {label_file}")
                        if "Package" in label or "Tctl" in label:
                            input_file = os.path.join(
                                hwmon_path, file.replace("_label", "_input")
                            )
                            if os.path.exists(input_file):
                                return input_file
        except Exception as e:
            print(f"Error reading {hwmon_path}: {e}")

    print("No suitable temperature sensor found.")
    return None

#################################################################

def get_channel_resource(path):
    with open(path, "r") as f:
        return int(f.read().strip()) / 1000

#################################################################

def cleanup(signum, frame):
    global stop_collection
    print("Stopping data collection...")
    stop_collection = True

#################################################################

def monitor_sample_count():
    global sample_count
    while not stop_collection:
        with count_lock:
            print(f"Total samples collected: {sample_count}")
        time.sleep(10)

#################################################################

def main():
    global stop_collection, sample_count

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    if len(sys.argv) < 2:
        print("Usage:\n \t<sampling_frequency>\n")
        sys.exit(1)
    
    sampling_frequency = int(sys.argv[1])
    
    temp_sensor_path = look_for_right_path()
    if temp_sensor_path is None:
        print("No suitable temperature sensor found. Exiting.")
        sys.exit(1)

    times = []
    temperatures = []

    print("Collecting samples. Press Ctrl+C to stop...")

    # Start the thread to monitor sample count
    count_thread = threading.Thread(target=monitor_sample_count)
    count_thread.start()

    start_time = time.time()
    while not stop_collection:
        current_time = time.time() - start_time
        temperature = get_channel_resource(temp_sensor_path)

        with count_lock:
            times.append(current_time)
            temperatures.append(temperature)
            sample_count += 1

        time.sleep(1 / sampling_frequency)

    count_thread.join()

    print("Data collection complete. Creating plot...")

    plt.figure(figsize=(12, 8))
    plt.plot(times, temperatures)
    plt.title("CPU Temperature Over Time")
    plt.xlabel("Time (seconds)")
    plt.ylabel("Temperature (°C)")
    plt.grid(True)
    plt.ylim(0, 100)

    plt.savefig("cpu_temperature_plot.png")
    print("Plot saved as cpu_temperature_plot.png")

    plt.show()

if __name__ == "__main__":
    main()