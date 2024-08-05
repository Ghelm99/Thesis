import time
import os
import multiprocessing
import numpy as np
import sys
from scipy.stats import norm
import utils


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


def get_baseline_cpu_vcore(
    path, baseline_sampling_duration, baseline_sampling_frequency, sigma_multiplier
):

    print("Computing baseline vcore...")

    sleep_duration = 1 / baseline_sampling_frequency
    samples_per_bit = int(baseline_sampling_duration * baseline_sampling_frequency)

    samples = []
    for _ in range(samples_per_bit):
        samples.append(utils.get_channel_resource(path))
        time.sleep(sleep_duration)

    samples.pop(0)
    mean_baseline = np.mean(samples)
    std_baseline = np.std(samples, ddof=1)
    vcore_threshold = mean_baseline + (sigma_multiplier * std_baseline)

    print(f"Baseline vcore: {mean_baseline:.2f} ± {std_baseline:.2f}.")
    print(f"Vcore threshold: {vcore_threshold:.2f}.")

    if mean_baseline is None:
        raise ValueError(
            "The 'mean_baseline' variable is None. Ensure it is correctly initialized."
        )

    return mean_baseline, std_baseline, vcore_threshold


#################################################################


def generate_cpu_load(target_load, duration):

    def worker(stop_event):
        start_time = time.time()
        while not stop_event.is_set() and time.time() - start_time < duration:
            end_time = time.time() + 0.01
            while time.time() < end_time:
                pass
            time.sleep(0.01 * (100 - target_load) / target_load)

    stop_event = multiprocessing.Event()
    processes = []
    num_cores = multiprocessing.cpu_count()

    for _ in range(num_cores):
        p = multiprocessing.Process(target=worker, args=(stop_event,))
        p.start()
        processes.append(p)

    time.sleep(duration)
    stop_event.set()

    for p in processes:
        p.join()

    print(f"CPU load of {target_load}% generated for {duration} seconds.")


#################################################################


def string_to_bits(input_string):
    bits = []
    for char in input_string:
        ascii_value = ord(char)
        binary_string = format(ascii_value, "08b")
        bits.extend(binary_string)
    return bits


#################################################################


def compute_average(samples, sampling_duration, sampling_frequency):

    window_size = int(sampling_duration * sampling_frequency)

    if len(samples) < window_size:
        return []

    avg = sum(samples) / len(samples)

    return [avg]


#################################################################


def get_significant_load(
    path,
    initial_load,
    load_step,
    load_sampling_duration,
    load_sampling_frequency,
    vcore_threshold,
):

    current_load = initial_load
    window_size = int(load_sampling_duration * load_sampling_frequency)

    while current_load < 100:
        print(f"Generating CPU load: {current_load}% for 10 seconds.")

        samples = []
        start_time = time.time()
        sleep_duration = 1 / load_sampling_frequency

        load_process = multiprocessing.Process(
            target=generate_cpu_load, args=(current_load, 10)
        )
        load_process.start()

        while time.time() - start_time < 10:
            samples.append(get_channel_resource(path))
            time.sleep(sleep_duration)

        load_process.join()

        if len(samples) >= window_size:

            avg = compute_average(
                samples, load_sampling_duration, load_sampling_frequency
            )

            print(f"Average vcore: {avg[0]:.2f}")

            if avg[0] > vcore_threshold:
                print(
                    f"Vcore: {avg[0]:.2f} is significantly different from baseline (threshold: {vcore_threshold:.2f})."
                )
                print(f"Load chosen for information encoding: {current_load}%.")
                return current_load

        print("Idle period...")
        time.sleep(10)
        current_load += load_step
