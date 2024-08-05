import time
import sys
import signal
import multiprocessing
import utils


########################################################################


def allocate_channel(load_percentage, bit_to_transmit, encoding_duration):

    print("Encoding bit: %s." % bit_to_transmit)

    if bit_to_transmit == 0:
        time.sleep(encoding_duration)
    else:
        process = multiprocessing.Process(
            target=utils.generate_cpu_load, args=(load_percentage, encoding_duration)
        )
        process.start()
        process.join(encoding_duration)
        if process.is_alive():
            process.terminate()
            process.join()


########################################################################


def main():

    signal.signal(signal.SIGINT, utils.cleanup)
    signal.signal(signal.SIGTERM, utils.cleanup)

    if len(sys.argv) != 10:
        print(
            "Usage:\n \t<secret>\n \t<baseline sampling duration>\n \t<baseline sampling frequency>\n \t<initial load>\n \t<load step>\n \t<load sampling duration>\n \t<load sampling frequency>\n \t<encoding duration>\n \t<sigma multiplier>\n"
        )
        return

    secret = sys.argv[1]
    baseline_sampling_duration = int(sys.argv[2])
    baseline_sampling_frequency = int(sys.argv[3])
    initial_load = int(sys.argv[4])
    load_step = int(sys.argv[5])
    load_sampling_duration = int(sys.argv[6])
    load_sampling_frequency = int(sys.argv[7])
    # handshake_duration = int(sys.argv[4])
    encoding_duration = int(sys.argv[8])
    sigma_multiplier = int(sys.argv[9])

    print("Starting the sender script...")
    print("Secret: %s." % secret)
    print("Baseline sampling duration: %s." % baseline_sampling_duration)
    print("Baseline sampling frequency: %s." % baseline_sampling_frequency)
    # print("Handshake duration: %s." % handshake_duration)
    print("Encoding duration: %s." % encoding_duration)
    print("Sigma multiplier: %s." % sigma_multiplier)

    path = utils.look_for_right_path()

    secret_bits = utils.string_to_bits(secret)

    path = utils.look_for_right_path()

    baseline_cpu_vcore, _, vcore_threshold = utils.get_baseline_cpu_vcore(
        path, baseline_sampling_duration, baseline_sampling_frequency, sigma_multiplier
    )

    current_load = utils.get_significant_load(
        path,
        initial_load,
        load_step,
        load_sampling_duration,
        load_sampling_frequency,
        vcore_threshold,
    )

    # utils.generate_handshake_signal(current_load, handshake_duration)

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

    for bit in secret_bits:
        allocate_channel(current_load, int(bit), float(encoding_duration))
    print("Secret transmitted.")


if __name__ == "__main__":
    main()
