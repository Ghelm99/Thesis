import subprocess
import time
import sys
import signal
import multiprocessing
import os


########################################################################


def look_for_right_path():
    print("Searching for sensors...")
    hwmon_dir = "/sys/class/hwmon"

    for hwmon in os.listdir(hwmon_dir):
        hwmon_path = os.path.join(hwmon_dir, hwmon)
        try:
            for file in os.listdir(hwmon_path):
                if file == "in0_input":
                    input_file = os.path.join(hwmon_path, file)
                    if os.path.exists(input_file):
                        return input_file
        except Exception as e:
            print(f"Error reading {hwmon_path}: {e}")

    print("No suitable sensor found.")
    return None


########################################################################


def get_channel_resource(path):
    with open(path, "r") as f:
        lines = f.readlines()
    return int(lines[0].strip()) / 1000


########################################################################


def cleanup(signum, frame):
    for process in multiprocessing.active_children():
        process.terminate()
        process.join()
    sys.exit(0)


########################################################################


def main():

    period = 3
    path = look_for_right_path()
    print(f"Selected path: {path}")
    if path is None:
        print("No suitable temperature sensor found. Exiting.")
        return

    if len(sys.argv) > 1:
        threshold = float(sys.argv[1])
    else:
        print("No command line argument provided for threshold. Using default.")
        threshold = 1.1

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    while True:
        current_time = time.time()
        if int(current_time) % 4 == 0:
            break
        time.sleep(0.1)

    secret_in_bits = []
    consecutive_zeros = 0
    previous_bit = 1

    while True:
        time.sleep(period / 2)
        vcore = get_channel_resource(path)
        if vcore > threshold:
            print(f"Bit received 1, Vcore: {vcore}.")
            secret_in_bits.append(1)
            previous_bit = 1
            consecutive_zeros = 0
        else:
            print(f"Bit received 0, Vcore: {vcore}.")
            secret_in_bits.append(0)
            if previous_bit == 0:
                consecutive_zeros += 1
            else:
                consecutive_zeros = 1
            previous_bit = 0
        time.sleep(period / 2)

        if consecutive_zeros == 10:
            print("Sequence of 10 zeros detected. Terminating.")
            print("Final secret in bits:", secret_in_bits)
            break


if __name__ == "__main__":
    main()
