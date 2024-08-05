#!/bin/bash

# Define the output file
output_file="installed_packages.txt"

# Get the list of all installed packages and save to the file
dpkg-query -f '${binary:Package}\n' -W | sort > "$output_file"

# Print a message indicating where the output was saved
echo "List of installed packages has been saved to $output_file"

# Optionally, display the number of packages
package_count=$(wc -l < "$output_file")
echo "Total number of installed packages: $package_count"