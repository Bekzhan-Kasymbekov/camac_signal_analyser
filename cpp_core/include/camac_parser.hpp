#pragma once

#include "camac_archive.hpp"

#include <array>
#include <cstdint>
#include <fstream>
#include <string>

std::uint16_t read_uint16_le(std::ifstream& file);

std::uint64_t get_file_size(std::ifstream& file);

camac_archive parse_camac_file(const std::string& file_path);

void export_channel_to_csv(
    const std::string& output_path,
    const std::array<std::uint16_t, samples_per_channel>& values
);
