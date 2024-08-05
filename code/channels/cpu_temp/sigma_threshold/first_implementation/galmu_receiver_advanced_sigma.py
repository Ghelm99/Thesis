import time
import sys
import signal
import multiprocessing
import numpy as np
from scipy.stats import norm
import receiver_initialization


########################################################################


def is_significantly_different(temp, temp_threshold):
    return temp > temp_threshold


########################################################################


def decode_secret(path, decoding_duration, decoding_frequency, temp_threshold):

    secret_in_bits = []
    consecutive_zeros = 0
    previous_bit = 1

    while True:
        samples = []
        start_time = time.time()

        while time.time() - start_time < decoding_duration:
            temp = receiver_initialization.get_channel_resource(path)
            samples.append(temp)
            time.sleep(1 / decoding_frequency)

        avg_temp = sum(samples) / len(samples)
        print(f"Average Temperature: {avg_temp}")

        if is_significantly_different(avg_temp, temp_threshold):
            print(f"Bit received 1, Average Temperature: {avg_temp}.")
            secret_in_bits.append(1)
            previous_bit = 1
            consecutive_zeros = 0
        else:
            print(f"Bit received 0, Average Temperature: {avg_temp}.")
            secret_in_bits.append(0)
            if previous_bit == 0:
                consecutive_zeros += 1
            else:
                consecutive_zeros = 1
            previous_bit = 0

        if consecutive_zeros == 10:
            print("Sequence of 10 zeros detected. Terminating.")
            print("Final secret in bits:", secret_in_bits)
            break

    return secret_in_bits


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

    if len(sys.argv) != 8:
        print(
            "Usage: <baseline sampling duration> <baseline sampling frequency> <handshake_duration> <handshake_frequency> <decoding duration> <decoding frequency> <sigma multiplier>"
        )
        return

    baseline_sampling_duration = int(sys.argv[1])
    baseline_sampling_frequency = int(sys.argv[2])
    handshake_duration = int(sys.argv[3])
    handshake_frequency = int(sys.argv[4])
    decoding_duration = int(sys.argv[5])
    decoding_frequency = int(sys.argv[6])
    sigma_multiplier = int(sys.argv[7])

    print("Starting the receiver script...")
    print("Baseline sampling duration: %s." % baseline_sampling_duration)
    print("Baseline sampling frequency: %s." % baseline_sampling_frequency)
    print("Decoding duration: %s." % decoding_duration)
    print("Decoding frequency: %s." % decoding_frequency)
    print("Sigma multiplier: %s." % sigma_multiplier)

    path = receiver_initialization.look_for_right_path()
    print(f"Selected path: {path}")
    if path is None:
        print("No suitable temperature sensor found. Exiting.")
        return

    _, _, temp_threshold = receiver_initialization.get_baseline_cpu_temp(
        path,
        int(baseline_sampling_duration),
        int(baseline_sampling_frequency),
        int(sigma_multiplier),
    )

    receiver_initialization.look_for_handshake(
        path, temp_threshold, handshake_duration, handshake_frequency
    )
    secret_in_bits = decode_secret(
        path, decoding_duration, decoding_frequency, temp_threshold
    )
    print("Secret in bits:", secret_in_bits)


if __name__ == "__main__":
    main()
