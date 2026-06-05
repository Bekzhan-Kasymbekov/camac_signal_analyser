#include "camac_parser.hpp"

#include <fstream>
#include <stdexcept>
#include <iomanip>

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

camac_event_time extract_old_ae_header_time(
    const std::array<std::uint16_t, samples_per_channel>& ae_raw
) {
    camac_event_time time;

    const std::uint32_t low_word = static_cast<std::uint32_t>(ae_raw[3]);
    const std::uint32_t high_word = static_cast<std::uint32_t>(ae_raw[4]);

    const std::uint32_t time_ticks = high_word * 65536U + low_word;

    time.absolute_seconds = static_cast<double>(time_ticks) * 1e-6;
    time.is_valid = true;

    return time;
}

camac_event_time extract_new_channel_timestamp(
    const std::array<std::uint16_t, samples_per_channel>& raw_values
) {
    camac_event_time time;

    const std::uint16_t seconds_millions = raw_values[0];
    const std::uint16_t seconds_thousands = raw_values[1];
    const std::uint16_t seconds_remainder = raw_values[2];
    const std::uint16_t milliseconds = raw_values[3];
    
    if (
        seconds_thousands > 999 ||
        seconds_remainder > 999 ||
        milliseconds > 999
    ) {
        time.is_valid = false;
        return time;
    }

    const std::uint64_t seconds =
        static_cast<std::uint64_t>(seconds_millions) * 1000000ULL +
        static_cast<std::uint64_t>(seconds_thousands) * 1000ULL +
        static_cast<std::uint64_t>(seconds_remainder);

    time.absolute_seconds =
        static_cast<double>(seconds) +
        static_cast<double>(milliseconds) / 1000.0;

    time.is_valid = true;

    return time;
}

void assign_relative_event_times(camac_archive& archive) {
    bool found_first_valid_time = false;
    double first_absolute_seconds = 0.0;

    for (auto& event : archive.events) {
        if (!event.event_time.is_valid) {
            continue;
        }

        if (!found_first_valid_time) {
            first_absolute_seconds = event.event_time.absolute_seconds;
            found_first_valid_time = true;
        }

        event.event_time.relative_seconds =
            event.event_time.absolute_seconds - first_absolute_seconds;

        if (event.ae_time.is_valid) {
            event.ae_time.relative_seconds =
                event.ae_time.absolute_seconds - first_absolute_seconds;
        }

        if (event.eme_time.is_valid) {
            event.eme_time.relative_seconds =
                event.eme_time.absolute_seconds - first_absolute_seconds;
        }

    }
}

camac_archive parse_camac_file(
        const std::string& file_path,
        camac_encoding_format encoding_format
) {
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

    const std::size_t ae_metadata_sample_count =
        get_ae_metadata_sample_count(encoding_format);

    const std::size_t eme_metadata_sample_count =
        get_eme_metadata_sample_count(encoding_format);

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

        event.event_index = event_index;
        
        if (encoding_format == camac_encoding_format::old_ae_header) {
            event.ae_time = extract_old_ae_header_time(event.ae_raw);
            event.event_time = event.ae_time;
        } else {
            event.ae_time = extract_new_channel_timestamp(event.ae_raw);
            event.eme_time = extract_new_channel_timestamp(event.eme_raw);
        
            if (event.ae_time.is_valid) {
                event.event_time = event.ae_time;
            } else if (event.eme_time.is_valid) {
                event.event_time = event.eme_time;
            }
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

    assign_relative_event_times(archive);

    return archive;
}

double calculate_max_abs(const std::vector<double>& signal) {
    double max_abs = 0.0;

    for (double value : signal) {
        const double abs_value = value < 0.0 ? -value : value;

        if (abs_value > max_abs) {
            max_abs = abs_value;
        }
    }

    return max_abs;
}

double calculate_energy(const std::vector<double>& signal) {
    double energy = 0.0;

    for (double value : signal) {
        energy += value * value;
    }

    return energy;
}

void export_archive_summary_to_csv(
    const std::string& output_path,
    const camac_archive& archive
) {
    std::ofstream out(output_path);

    if (!out) {
        throw std::runtime_error("Could not create CSV file: " + output_path);
    }

    out << std::fixed << std::setprecision(6);

    out << "event_index,"
        << "time_valid,"
        << "absolute_seconds,"
        << "relative_seconds,"
        << "ae_max_abs,"
        << "eme_max_abs,"
        << "ae_energy,"
        << "eme_energy\n";

    for (std::size_t event_index = 0; event_index < archive.events.size(); ++event_index) {
        const auto& event = archive.events[event_index];

        const double ae_max_abs = calculate_max_abs(event.ae_signal);
        const double eme_max_abs = calculate_max_abs(event.eme_signal);

        const double ae_energy = calculate_energy(event.ae_signal);
        const double eme_energy = calculate_energy(event.eme_signal);

        out << event_index << ','
            << event.event_time.is_valid << ','
            << event.event_time.absolute_seconds << ','
            << event.event_time.relative_seconds << ','
            << ae_max_abs << ','
            << eme_max_abs << ','
            << ae_energy << ','
            << eme_energy << '\n';
    }
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
    const std::vector<double>& values,
    std::size_t metadata_sample_count
) {
    std::ofstream out(output_path);

    if (!out) {
        throw std::runtime_error("Could not create CSV file: " + output_path);
    }

    out << "sample_index,raw_sample_index,signal_value,time_microseconds\n";

    for (std::size_t i = 0; i < values.size(); ++i) {
        const std::size_t raw_sample_index = i + metadata_sample_count;

        const double time_microseconds =
            static_cast<double>(i) * tact_seconds * 1'000'000.0;

        out << i << ',' 
            << raw_sample_index << ','
            << values[i] << ',' 
            << time_microseconds << '\n';
    }
}
