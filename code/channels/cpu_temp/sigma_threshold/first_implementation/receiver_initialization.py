import time
import subprocess
import os
import multiprocessing
import numpy as np
import sys
import time
from collections import deque


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


def cleanup(signum, frame):
    for process in multiprocessing.active_children():
        process.terminate()
        process.join()
    sys.exit(0)


########################################################################


def look_for_handshake(path, temp_threshold, handshake_duration, handshake_frequency):

    print("Waiting for the handshake...")

    temps = deque()
    samples = 0
    sum_temps = 0

    while True:
        temp = get_channel_resource(path)
        temps.append(temp)
        sum_temps += temp
        samples += 1

        # If we've collected more samples than needed for the handshake duration,
        # remove the oldest sample
        if samples > handshake_duration / handshake_frequency:
            sum_temps -= temps.popleft()
            samples -= 1

        # Calculate the average of the current window
        avg_temp = sum_temps / samples

        if avg_temp > temp_threshold:
            print(f"Handshake successful, starting decoding...")
            return True

        time.sleep(handshake_frequency)


########################################################################
