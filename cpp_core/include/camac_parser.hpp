#pragma once

#include "camac_archive.hpp"

#include <array>
#include <cstdint>
#include <fstream>
#include <string>
#include <vector>

std::uint16_t read_uint16_le(std::ifstream& file);

std::uint64_t get_file_size(std::ifstream& file);

std::vector<double> make_mean_subtracted_signal(
    const std::array<std::uint16_t, samples_per_channel>& raw_values,
    std::size_t metadata_sample_count
);

camac_archive parse_camac_file(const std::string& file_path);

camac_archive parse_camac_file(
    const std::string& file_path,
    camac_encoding_format encoding_format
);

void export_channel_to_csv(
    const std::string& output_path,
    const std::array<std::uint16_t, samples_per_channel>& values
);

void export_signal_to_csv(
    const std::string& output_path,
    const std::vector<double>& values,
    std::size_t metadata_sample_count
);

double calculate_max_abs(const std::vector<double>& signal);

double calculate_energy(const std::vector<double>& signal);

camac_event_time extract_old_ae_header_time(
    const std::array<std::uint16_t, samples_per_channel>& ae_raw
);

camac_event_time extract_new_channel_timestamp(
    const std::array<std::uint16_t, samples_per_channel>& raw_values
);

void assign_relative_event_times(camac_archive& archive);

void export_archive_summary_to_csv(
    const std::string& output_path,
    const camac_archive& archive
);
