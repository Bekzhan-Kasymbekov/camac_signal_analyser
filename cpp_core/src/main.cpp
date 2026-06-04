#include "camac_parser.hpp"

#include <exception>
#include <fstream>
#include <iostream>
#include <string>

void print_first_values(
    const std::string& title,
    const std::array<std::uint16_t, samples_per_channel>& values
) {
    std::cout << title << '\n';

    for (std::size_t i = 0; i < 10; ++i) {
        std::cout << i << ": " << values[i] << '\n';
    }
}

void solve() {
    std::string file_path;

    std::cout << "Enter CAMAC binary file path: ";
    std::cin >> file_path;

    std::ifstream file(file_path, std::ios::binary);

    if (!file) {
        throw std::runtime_error("Could not open file: " + file_path);
    }

    const std::uint64_t file_size = get_file_size(file);
    file.close();

    const camac_archive archive = parse_camac_file(file_path);

    std::cout << "\n";
    std::cout << "File size: " << file_size << " bytes\n";
    std::cout << "Bytes per event: " << bytes_per_event << " bytes\n";
    std::cout << "Events: " << archive.events.size() << '\n';
    std::cout << "Samples per channel: " << samples_per_channel << '\n';
    std::cout << "Sample rate: " << sample_rate_hz << " Hz\n";
    std::cout << "Tact time: " << tact_seconds * 1'000'000.0 << " microseconds\n";
    std::cout << "Event duration: " 
              << samples_per_channel * tact_seconds * 1000.0
              << "ms\n";

    if (archive.events.empty()) {
        std::cout << "Archive has no events.\n";
        return;
    }

    const auto& first_event = archive.events.front();

    std::cout << '\n';
    print_first_values("First 10 raw AE values:", first_event.ae_raw);

    std::cout << '\n';
    print_first_values("First 10 raw EME values:", first_event.eme_raw);

    export_channel_to_csv("../../exports/first_event_ae.csv", first_event.ae_raw);
    export_channel_to_csv("../../exports/first_event_eme.csv", first_event.eme_raw);

    std::cout << '\n';
    std::cout << "Exported:\n";
    std::cout << "- exports/first_event_ae.csv\n";
    std::cout << "- exports/first_event_eme.csv\n";
}

int main() {
    try {
        solve();
    } catch (const std::exception& error) {
        std::cerr << "Error: " << error.what() << '\n';
        return 1;
    }

    return 0;
}
