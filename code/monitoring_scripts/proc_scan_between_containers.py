import os
import subprocess
import sys
import stat
import csv


################################################################


# Function used to check whether a directory is a PID directory
def is_pid_directory(name):
    return name.isdigit()


################################################################


# Function to convert file permissions to a string like 'rwxr-xr-x'
def get_file_permissions(path):
    file_stat = os.stat(path)
    return stat.filemode(file_stat.st_mode)


################################################################


# Function to write data to a CSV file
def write_to_csv(filename, data, headers=None):
    with open(filename, "w", newline="") as file:
        writer = csv.writer(file)
        if headers:
            writer.writerow(headers)
        writer.writerows(data)


################################################################


# Function to list file names and their permissions in the container
def list_container_file_names(container_id, container_path):
    try:
        cmd = f"docker exec -it {container_id} sh -c \"find {container_path} -type f -exec stat -c '%n,%A' {{}} \\;\""
        process = subprocess.Popen(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        output, error = process.communicate()
        if process.returncode != 0:
            print(f"Error listing files in container {container_id}: {error}")
            return []
        return sorted(
            [
                line.split(",")
                for line in output.strip().split("\n")
                if not is_pid_directory(os.path.basename(line.split(",")[0]))
            ]
        )
    except Exception as e:
        print(f"An error occurred while listing container files: {e}")
        return []


################################################################


# Function used to compare files and permissions between the host and the container
def compare_files(container_1_id, container_2_id, file_path):
    try:
        # Execute sha512sum command in container 1
        container_1_cmd = f'docker exec -it {container_1_id} sh -c "sha512sum {file_path} && stat -c %A {file_path}"'
        container_1_process = subprocess.Popen(
            container_1_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        container_1_output, container_error = container_1_process.communicate()

        # Check if file not found in the container
        if container_1_process.returncode != 0:
            print(f"File '{file_path}' not found in container {container_1_id}.")
            return False

        # Execute sha512sum command in container 2
        container_2_cmd = f'docker exec -it {container_2_id} sh -c "sha512sum {file_path} && stat -c %A {file_path}"'
        container_2_process = subprocess.Popen(
            container_2_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        container_2_output, container_error = container_2_process.communicate()

        # Check if file not found in the container
        if container_2_process.returncode != 0:
            print(f"File '{file_path}' not found in container {container_2_id}.")
            return False

        # Extract hash and permissions from container output 1
        container_1_file_hash = container_1_output.split()[0]
        container_1_file_permissions = container_1_output.split()[1]

        # Extract hash and permissions from container output 1
        container_2_file_hash = container_2_output.split()[0]
        container_2_file_permissions = container_2_output.split()[1]

        # Comparing hashes and permissions
        return (container_1_file_hash == container_2_file_hash) and (
            container_1_file_permissions == container_2_file_permissions
        )
    except Exception as e:
        print(f"An error occurred: {e}")
        return False


################################################################


# Function used to look for a substring in a list of strings
def find_element(string_list, substring):
    return next((s for s in string_list if substring in s[0]), None)


################################################################


# Main function
def main():

    # Checking if the container ID was provided as an argument
    if len(sys.argv) != 4:
        print(
            "Usage: python3 script_name.py <container_id_1> <container_id_2> <filesystem_directory>"
        )
        sys.exit(1)

    # Extracting the container_1 ID from command-line arguments
    container_1_id = sys.argv[1]

    # Extracting the container_2 ID from command-line arguments
    container_2_id = sys.argv[2]

    # Extracting the directory to analyze (/proc, /sys, etc.)
    directory = sys.argv[3]

    # Building a list of all container file names with permissions
    container_1_file_names = list_container_file_names(container_1_id, directory)

    # Building a list of all container file names with permissions
    container_2_file_names = list_container_file_names(container_2_id, directory)

    # Creating a directory for the results
    os.makedirs("script_results", exist_ok=True)

    # Building a list of all files shared between the host and the container
    equal_file_names = []
    for container_1_file_path, container_1_permissions in container_1_file_names:
        if compare_files(container_1_id, container_2_id, container_1_file_path):
            container_2_line = find_element(
                container_2_file_names, container_1_file_path
            )
            container_2_permissions = container_2_line[1] if container_2_line else ""
            equal_file_names.append(
                [
                    container_1_file_path,
                    container_1_permissions,
                    container_2_permissions,
                ]
            )

    # Building a list of all writable files shared between the host and the container (files must have the same permissions)
    equal_writable_file_names = []
    for (
        container_1_file_path,
        container_1_permissions,
        container_2_permissions,
    ) in equal_file_names:
        if container_1_permissions != container_2_permissions:
            print(
                f"Permissions for file '{container_1_file_path}' do not match between container 1 and container 2."
            )
        else:
            if "w" in container_1_permissions and "w" in container_2_permissions:
                equal_writable_file_names.append(
                    [
                        container_1_file_path,
                        container_1_permissions,
                        container_2_permissions,
                    ]
                )
            if "d" in container_1_permissions and "d" in container_2_permissions:
                equal_writable_file_names.append(
                    [
                        container_1_file_path,
                        container_1_permissions,
                        container_2_permissions,
                    ]
                )
                equal_writable_file_names.append("")

    # Writing to output files
    write_to_csv(
        "script_results/container_1_file_names.csv",
        container_1_file_names,
        ["File Path", "Permissions"],
    )
    write_to_csv(
        "script_results/container_2_file_names.csv",
        container_2_file_names,
        ["File Path", "Permissions"],
    )
    write_to_csv(
        "script_results/equal_file_names.csv",
        equal_file_names,
        ["File Path", "Container 1 permissions", "Container 2 permissions"],
    )
    write_to_csv(
        "script_results/equal_writable_file_names.csv",
        equal_writable_file_names,
        ["File Path", "Container 1 permissions", "Container 2 permissions"],
    )


if __name__ == "__main__":
    main()
