#include "camac_parser.hpp"

#include <fstream>
#include <stdexcept>

std::uint16_t read_uint16_le(std::ifstream& file) {
    unsigned char bytes[2]{};
    file.read(reinterpret_cast<char*>(bytes), 2);

    if (!file) {
        throw std::runtime_error("Unexpected end of file while reading uint16");
    }

    return static_cast<std::uint16_t>(bytes[0] | (bytes[1] << 8));
}   

std::uint64_t get_file_size(std::ifstream& file) {
    file.seekg(0, std::ios::end);
    const auto size = file.tellg();
    file.seekg(0, std::ios::beg);

    if (size < 0) {
        throw std::runtime_error("Could not determine file size");
    }

    return static_cast<std::uint64_t>(size);
}

std::vector<double> make_mean_subtracted_signal(
    const std::array<std::uint16_t, samples_per_channel>& raw_values,
    std::size_t metadata_sample_count
) {
    if (metadata_sample_count >= samples_per_channel) {
        throw std::runtime_error("Metadata sample count is too large");
    }
    
    std::vector<double> signal;
    signal.reserve(samples_per_channel - metadata_sample_count);

    double sum = 0.0;

    for (std::size_t i = metadata_sample_count; i < samples_per_channel; ++i) {
        sum += static_cast<double>(raw_values[i]);
    }

    const double mean =
        sum / static_cast<double>(samples_per_channel -  metadata_sample_count);

    for (std::size_t i = metadata_sample_count; i < samples_per_channel; ++i) {
        signal.push_back(static_cast<double>(raw_values[i]) - mean);
    }

    return signal;
}

camac_archive parse_camac_file(const std::string& file_path) {
    std::ifstream file(file_path, std::ios::binary);

    if (!file) {
        throw std::runtime_error("Could not open file: " + file_path);
    }

    const std::uint64_t file_size = get_file_size(file);

    if (file_size % bytes_per_event != 0) {
        throw std::runtime_error(
            "Invalid file size. File size is not divisible by CAMAC event size."
        );
    }

    const std::size_t event_count =
        static_cast<std::size_t>(file_size / bytes_per_event);

    camac_archive archive;
    archive.events.resize(event_count);

    for (std::size_t event_index = 0; event_index < event_count; ++event_index) {
        auto& event = archive.events[event_index];

        for (std::size_t i = 0; i < samples_per_channel; ++i) {
            event.ae_raw[i] = read_uint16_le(file);
        }

        for (std::size_t i = 0; i < samples_per_channel; ++i) {
            event.eme_raw[i] = read_uint16_le(file);
        }

        event.ae_signal = make_mean_subtracted_signal(
            event.ae_raw,
            ae_metadata_sample_count
        );

        event.eme_signal = make_mean_subtracted_signal(
            event.eme_raw,
            eme_metadata_sample_count
        );
    }

    return archive;
}

void export_channel_to_csv(
    const std::string& output_path,
    const std::array<std::uint16_t, samples_per_channel>& values
) {
    std::ofstream out(output_path);

    if (!out) {
        throw std::runtime_error("Could not create CSV file: " + output_path);
    }

    out << "sample_index,raw_value,time_microseconds\n";

    for (std::size_t i = 0; i < samples_per_channel; ++i) {
        const double time_microseconds =
            static_cast<double>(i) * tact_seconds * 1'000'000.0;

        out << i << ',' << values[i] << ',' << time_microseconds << '\n';
    }
}

void export_signal_to_csv(
    const std::string& output_path,
    const std::vector<double>& values
) {
    std::ofstream out(output_path);

    if (!out) {
        throw std::runtime_error("Could not create CSV file: " + output_path);
    }

    out << "sample_index,signal_value,time_microseconds\n";

    for (std::size_t i = 0; i < values.size(); ++i) {
        const double time_microseconds =
            static_cast<double>(i) * tact_seconds * 1'000'000.0;

        out << i << ',' << values[i] << ',' << time_microseconds << '\n';
    }
}
