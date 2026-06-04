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

void export_channel_to_csv(
    const std::string& output_path,
    const std::array<std::uint16_t, samples_per_channel>& values
);

void export_signal_to_csv(
    const std::string& output_path,
    const std::vector<double>& values
);

double calculate_max_abs(const std::vector<double>& signal);

double calculate_energy(const std::vector<double>& signal);

void export_archive_summary_to_csv(
    const std::string& output_path,
    const camac_archive& archive
);
