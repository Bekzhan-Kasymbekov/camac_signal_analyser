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
    const std::string sample_data_directory = "../../sample_data/";

    std::string file_name;

    std::cout << "Enter CAMAC binary file name from sample_data/: ";
    std::cin >> file_name;

    const std::string file_path = sample_data_directory + file_name;

    std::ifstream file(file_path, std::ios::binary);

    if (!file) {
        throw std::runtime_error("Could not open file: " + file_path);
    }

    const std::uint64_t file_size = get_file_size(file);
    file.close();

    int format_choice = 0;

    std::cout << "Select encoding format:\n";
    std::cout << "1. Old format: AE header, EME untouched\n";
    std::cout << "2. New format: AE and EME timestamps\n";
    std::cout << "Choice: \n";
    std::cin >> format_choice;

    camac_encoding_format encoding_format = camac_encoding_format::old_ae_header;

    if (format_choice == 1) {
        encoding_format = camac_encoding_format::old_ae_header;
    } else if (format_choice == 2) {
        encoding_format = camac_encoding_format::new_channel_timestamps;
    } else {
        throw std::runtime_error("Invalid encoding format choice");
    }

    const camac_archive archive = parse_camac_file(file_path, encoding_format);

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

    std::size_t selected_event_index = 0;

    std::cout << '\n';
    std::cout << "Enter event index to export, 0 to "
              << archive.events.size() - 1 << ": ";
    std::cin >> selected_event_index;

    if (selected_event_index >= archive.events.size()) {
        throw std::runtime_error("Selected event index is out of range");
    }

    const auto& selected_event = archive.events[selected_event_index];

    std::cout << '\n';
    std::cout << "Selected event: " << selected_event_index << '\n';

    std::cout << '\n';
    print_first_values("First 10 raw AE values:", selected_event.ae_raw);

    std::cout << '\n';
    print_first_values("First 10 raw EME values:", selected_event.eme_raw);

    const std::string event_prefix =
        "../../exports/event_" + std::to_string(selected_event_index);

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
    std::cout << "- exports/event_" << selected_event_index << "_ae_raw.csv\n";
    std::cout << "- exports/event_" << selected_event_index << "_eme_raw.csv\n";
    std::cout << "- exports/event_" << selected_event_index << "_ae_signal.csv\n";
    std::cout << "- exports/event_" << selected_event_index << "_eme_signal.csv\n";
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
