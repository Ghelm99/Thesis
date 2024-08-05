import time
import os
import sys
import signal
import multiprocessing
import random

########################################################################


def allocate_channel(bit_to_transmit, period, precision, core):

    def generate_load_on_one_core(precision, core):
        os.sched_setaffinity(0, {core})
        while True:
            for _ in range(precision):
                _ = random.random() ** 0.5

    if bit_to_transmit == 0:
        time.sleep(period)
    else:
        process = multiprocessing.Process(
            target=generate_load_on_one_core, args=(precision, core)
        )
        process.start()
        time.sleep(period)
        process.terminate()
        process.join()


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


def main():

    period = 3
    precision = 1000

    if len(sys.argv) > 1:
        secret = sys.argv[1]
    else:
        print("No command line argument provided.")
        return

    secret_bits = string_to_bits(secret)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    processes = []
    cores = list(range(multiprocessing.cpu_count()))

    while True:
        current_time = time.time()
        if int(current_time) % 4 == 0:
            break
        time.sleep(0.1)

    for bit in secret_bits:
        print("Encoding bit: %s." % bit)
        for core in cores:
            process = multiprocessing.Process(
                target=allocate_channel, args=(int(bit), period, precision, core)
            )
            process.start()
            processes.append(process)
        for process in processes:
            process.join()

    print("Secret transmitted.")


if __name__ == "__main__":
    main()
