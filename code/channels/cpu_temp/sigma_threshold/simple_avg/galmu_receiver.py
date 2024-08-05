import time
import sys
import signal
import numpy as np
from scipy.stats import norm
import utils


########################################################################


def decode_secret(path, decoding_duration, sampling_frequency, temp_threshold):

    print("Decoding secret...")
    secret_in_bits = []
    consecutive_zeros = 0
    sleep_duration = 1 / sampling_frequency
    samples_per_bit = int(decoding_duration * sampling_frequency)

    while True:
        samples = []
        for _ in range(samples_per_bit):
            samples.append(utils.get_channel_resource(path))
            time.sleep(sleep_duration)

        avg = utils.compute_average(samples, decoding_duration, sampling_frequency)

        print(f"AVG array: {avg}")

        if avg[0] > temp_threshold:
            print(
                f"Decoded bit: 1, AVG: {avg[0]:.2f}, Threshold: {temp_threshold:.2f}."
            )
            bit = 1
            consecutive_zeros = 0
        else:
            print(
                f"Decoded bit: 0, AVG: {avg[0]:.2f}, Threshold: {temp_threshold:.2f}."
            )
            bit = 0
            consecutive_zeros += 1

        secret_in_bits.append(bit)

        if consecutive_zeros == 10:
            print("Sequence of 10 zeros detected. Terminating.")
            print("Final secret in bits:", secret_in_bits)
            break

    return secret_in_bits


########################################################################


def main():

    signal.signal(signal.SIGINT, utils.cleanup)
    signal.signal(signal.SIGTERM, utils.cleanup)

    if len(sys.argv) != 6:
        print(
            "Usage:\n \t<baseline sampling duration>\n \t<baseline sampling frequency>\n \t<decoding duration>\n \t<decoding frequency>\n \t<sigma multiplier>\n"
        )
        return

    baseline_sampling_duration = int(sys.argv[1])
    baseline_sampling_frequency = int(sys.argv[2])
    decoding_duration = int(sys.argv[3])
    decoding_frequency = int(sys.argv[4])
    sigma_multiplier = int(sys.argv[5])

    print("Starting the receiver script...")
    print("Baseline sampling duration: %s." % baseline_sampling_duration)
    print("Baseline sampling frequency: %s." % baseline_sampling_frequency)
    print("Decoding duration: %s." % decoding_duration)
    print("Decoding frequency: %s." % decoding_frequency)
    print("Sigma multiplier: %s." % sigma_multiplier)

    path = utils.look_for_right_path()
    print(f"Selected path: {path}")
    if path is None:
        print("No suitable temperature sensor found. Exiting.")
        return

    baseline_cpu_temp, _, temp_threshold = utils.get_baseline_cpu_temp(
        path,
        baseline_sampling_duration,
        baseline_sampling_frequency,
        sigma_multiplier,
    )

    # utils.look_for_handshake(path, temp_threshold, handshake_frequency)

    print("Waiting for synchronization...")
    while True:
        user_input = input("Press Enter to continue...")
        if user_input == "":
            break
        time.sleep(0.1)

    while True:
        current_time = time.localtime()
        seconds = current_time.tm_sec
        if seconds % 11 == 0:
            break
        time.sleep(0.1)

    secret_in_bits = decode_secret(
        path, decoding_duration, decoding_frequency, temp_threshold
    )
    print("Secret in bits:", secret_in_bits)


if __name__ == "__main__":
    main()
