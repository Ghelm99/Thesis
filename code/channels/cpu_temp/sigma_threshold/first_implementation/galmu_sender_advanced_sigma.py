import time
import sys
import signal
import multiprocessing
import numpy as np
from scipy.stats import norm
import sender_initialization


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


def allocate_channel(load_percentage, bit_to_transmit, encoding_duration):

    print("Encoding bit: %s." % bit_to_transmit)

    if bit_to_transmit == 0:
        time.sleep(encoding_duration)
    else:
        process = multiprocessing.Process(
            target=generate_cpu_load, args=(load_percentage, encoding_duration)
        )
        process.start()
        time.sleep(encoding_duration)
        process.terminate()
        process.join()


########################################################################


def cleanup(signum, frame):
    for process in multiprocessing.active_children():
        process.terminate()
        process.join()
    sys.exit(0)


########################################################################


def main():

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    if len(sys.argv) != 7:
        print(
            "Usage: <secret> <baseline sampling duration> <baseline sampling frequency> <handshake_duration> <encoding duration> <sigma multiplier>"
        )
        return

    secret = sys.argv[1]
    baseline_sampling_duration = int(sys.argv[2])
    baseline_sampling_frequency = int(sys.argv[3])
    handshake_duration = int(sys.argv[4])
    encoding_duration = int(sys.argv[5])
    sigma_multiplier = int(sys.argv[6])

    print("Starting the sender script...")
    print("Secret: %s." % secret)
    print("Baseline sampling duration: %s." % baseline_sampling_duration)
    print("Baseline sampling frequency: %s." % baseline_sampling_frequency)
    print("Encoding duration: %s." % encoding_duration)
    print("Sigma multiplier: %s." % sigma_multiplier)

    secret_bits = sender_initialization.string_to_bits(secret)

    load_percentage = sender_initialization.initialization(
        baseline_sampling_duration,
        baseline_sampling_frequency,
        handshake_duration,
        sigma_multiplier,
    )

    while True:
        current_time = time.time()
        if int(current_time) % 4 == 0:
            break
        time.sleep(0.1)

    for bit in secret_bits:
        allocate_channel(load_percentage, int(bit), float(encoding_duration))
    print("Secret transmitted.")


if __name__ == "__main__":
    main()
