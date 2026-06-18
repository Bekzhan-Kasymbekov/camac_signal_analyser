#include "camac_parser.hpp"

#include <array>
#include <cstdint>
#include <exception>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>

std::string encoding_format_to_string(camac_encoding_format encoding_format) {
    if (encoding_format == camac_encoding_format::old_ae_header) {
        return "old_ae_header";
    }

    if (encoding_format == camac_encoding_format::new_channel_timestamps) {
        return "new_channel_timestamps";
    }

    return "auto_detect";
}

std::string resolve_file_path(const std::string& input_path) {
    std::ifstream direct_file(input_path, std::ios::binary);

    if (direct_file) {
        return input_path;
    }

    const std::string sample_data_path = "../../sample_data/" + input_path;

    std::ifstream sample_data_file(sample_data_path, std::ios::binary);

    if (sample_data_file) {
        return sample_data_path;
    }

    throw std::runtime_error(
        "Could not open file directly or from sample_data/: " + input_path
    );
}

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
    std::string input_path;

    std::cout << "Enter CAMAC binary file name from sample_data/ or full path: ";
    std::cin >> input_path;


    const std::string file_path = resolve_file_path(input_path);

    std::ifstream file(file_path, std::ios::binary);

    if (!file) {
        throw std::runtime_error("Could not open file: " + file_path);
    }

    const std::uint64_t file_size = get_file_size(file);
    file.close();

    const camac_encoding_format encoding_format =
        detect_camac_encoding_format(file_path);

    const camac_archive archive = parse_camac_file(file_path, encoding_format);

    std::cout << "\n";
    std::cout << "File: " << file_path << '\n';
    std::cout << "Detected format: "
              << encoding_format_to_string(encoding_format) << '\n';
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

    std::size_t selected_event_number = 1;

    std::cout << '\n';
    std::cout << "Enter event number to export, 1 to "
              << archive.events.size() << ": ";
    std::cin >> selected_event_number;

    if (
        selected_event_number < 1 ||
        selected_event_number > archive.events.size()
    ) {
        throw std::runtime_error("Selected event number is out of range");
    }

    const std::size_t selected_event_index = selected_event_number - 1;
    const auto& selected_event = archive.events[selected_event_index];

    std::cout << '\n';
    std::cout << "Selected event: " << selected_event_number << '\n';

    std::cout << '\n';
    print_first_values("First 10 raw AE values:", selected_event.ae_raw);

    std::cout << '\n';
    print_first_values("First 10 raw EME values:", selected_event.eme_raw);

    const std::string event_prefix =
        "../../exports/event_" + std::to_string(selected_event_number);

    const std::string ae_raw_path = event_prefix + "_ae_raw.csv";
    const std::string eme_raw_path = event_prefix + "_eme_raw.csv";
    const std::string ae_signal_path = event_prefix + "_ae_signal.csv";
    const std::string eme_signal_path = event_prefix + "_eme_signal.csv";

    export_channel_to_csv(ae_raw_path, selected_event.ae_raw);
    export_channel_to_csv(eme_raw_path, selected_event.eme_raw);

    export_signal_to_csv(
            ae_signal_path,
            selected_event.ae_signal,
            get_ae_metadata_sample_count(encoding_format)
    );

    export_signal_to_csv(
            eme_signal_path,
            selected_event.eme_signal,
            get_eme_metadata_sample_count(encoding_format)
    );

    export_archive_summary_to_csv("../../exports/archive_summary.csv", archive);

    std::cout << '\n';
    std::cout << "Exported selected event " << selected_event_index << ":\n";
    std::cout << "- exports/event_" << selected_event_number << "_ae_raw.csv\n";
    std::cout << "- exports/event_" << selected_event_number << "_eme_raw.csv\n";
    std::cout << "- exports/event_" << selected_event_number << "_ae_signal.csv\n";
    std::cout << "- exports/event_" << selected_event_number << "_eme_signal.csv\n";
    std::cout << "- exports/archive_summary.csv\n";

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
