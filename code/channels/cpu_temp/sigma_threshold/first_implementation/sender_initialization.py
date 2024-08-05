import signal
import time
import subprocess
import os
import multiprocessing
import numpy as np
import sys


########################################################################


def is_intel_cpu():
    try:
        result = subprocess.run(
            ["grep", "-i", "vendor_id", "/proc/cpuinfo"],
            capture_output=True,
            text=True,
            check=True,
        )
        return "GenuineIntel" in result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error checking CPU type: {e}")
        return False


########################################################################


def look_for_right_path():

    print("Checking CPU type...")
    if is_intel_cpu():
        print("Intel CPU detected")
    else:
        print("AMD CPU detected")

    print("Searching for temperature sensors...")
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


########################################################################


def get_channel_resource(path):
    with open(path, "r") as f:
        lines = f.readlines()
    return int(lines[0].strip()) / 1000


########################################################################


def get_baseline_cpu_temp(
    path, baseline_sampling_duration, baseline_sampling_frequency, sigma_multiplier
):

    print("Computing baseline temperature...")

    temps = []
    start_time = time.time()

    while time.time() - start_time < baseline_sampling_duration:
        temps.append(get_channel_resource(path))
        time.sleep(1 / baseline_sampling_frequency)

    mean_baseline = np.mean(temps)
    std_baseline = np.std(temps, ddof=1)
    temp_threshold = mean_baseline + (sigma_multiplier * std_baseline)

    print(f"Baseline temperature: {mean_baseline:.2f} ± {std_baseline:.2f}")
    print(f"Temperature threshold: {temp_threshold:.2f}")

    if mean_baseline is None:
        raise ValueError(
            "The 'mean_baseline' variable is None. Ensure it is correctly initialized."
        )

    return mean_baseline, std_baseline, temp_threshold


########################################################################


def is_significantly_different(temp, temp_threshold):
    return temp > temp_threshold


########################################################################


def generate_cpu_load(load_percentage, duration):

    load_time = load_percentage / 100.0
    interval = 0.01

    def worker():
        end_time = time.time() + duration
        while time.time() < end_time:
            start = time.time()
            while (time.time() - start) < load_time * interval:
                pass
            time.sleep((1 - load_time) * interval)

    num_cores = multiprocessing.cpu_count()
    processes = []

    for _ in range(num_cores):
        p = multiprocessing.Process(target=worker)
        p.start()
        processes.append(p)

    for p in processes:
        p.join()


########################################################################


def cleanup(signum, frame):
    for process in multiprocessing.active_children():
        process.terminate()
        process.join()
    sys.exit(0)


########################################################################


def string_to_bits(input_string):
    bits = []
    for char in input_string:
        ascii_value = ord(char)
        binary_string = format(ascii_value, "08b")
        bits.extend(binary_string)
    return bits


########################################################################


def get_significant_load(path, sampling_frequency, temp_threshold):

    current_load = 10
    while current_load < 100:
        print(f"Generating CPU load: {current_load}% for 10 seconds.")

        load_process = multiprocessing.Process(
            target=generate_cpu_load, args=(current_load, 10)
        )
        load_process.start()

        temps = []
        start_time = time.time()
        while time.time() - start_time < 10:
            temps.append(get_channel_resource(path))
            time.sleep(1 / sampling_frequency)

        load_process.join()
        mean_temp = np.mean(temps)
        print(f"Current temperature: {mean_temp:.2f}")
        if is_significantly_different(mean_temp, temp_threshold):
            print(
                f"Temperature: {mean_temp:.2f} is significantly different from baseline (threshold: {temp_threshold:.2f})."
            )
            break
        current_load += 2.5

    print(f"Load chosen for information encoding: {current_load}%.")
    return current_load


########################################################################


def generate_handshake_signal(load_percentage, handshake_duration):
    print("Generating handshake signal...")
    time.sleep(5)
    generate_cpu_load(load_percentage, handshake_duration)


########################################################################


def initialization(
    baseline_sampling_duration,
    baseline_sampling_frequency,
    handshake_duration,
    sigma_multiplier,
):

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    path = look_for_right_path()

    _, _, temp_threshold = get_baseline_cpu_temp(
        path, baseline_sampling_duration, baseline_sampling_frequency, sigma_multiplier
    )

    current_load = get_significant_load(
        path, baseline_sampling_frequency, temp_threshold
    )

    generate_handshake_signal(current_load, handshake_duration)

    return current_load
