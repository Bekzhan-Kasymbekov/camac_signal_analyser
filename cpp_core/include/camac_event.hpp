#pragma once

#include <array>
#include <cstdint>
#include <cstddef>
#include <vector>

enum class camac_encoding_format {
    old_ae_header,
    new_channel_timestamps
};

constexpr std::size_t samples_per_channel = 3072;
constexpr std::size_t channels_per_event = 2;
constexpr std::size_t bytes_per_sample = sizeof(std::uint16_t);

constexpr std::size_t bytes_per_event =
    samples_per_channel * channels_per_event * bytes_per_sample;

inline std::size_t get_ae_metadata_sample_count(camac_encoding_format format) {
    if (format == camac_encoding_format::old_ae_header) {
        return 12;
    }

    return 4;
}

inline std::size_t get_eme_metadata_sample_count(camac_encoding_format format) {
    if (format == camac_encoding_format::old_ae_header) {
        return 0;
    }

    return 4;
}

constexpr double tact_seconds = 500e-9;
constexpr double sample_rate_hz = 1.0 / tact_seconds;

struct camac_event_time {
    double absolute_seconds = 0.0;
    double relative_seconds = 0.0;
    bool is_valid = false;
};

struct camac_event {
    std::array<std::uint16_t, samples_per_channel> ae_raw{};
    std::array<std::uint16_t, samples_per_channel> eme_raw{};

    std::vector<double> ae_signal;
    std::vector<double> eme_signal;

    camac_event_time ae_time;
    camac_event_time eme_time;
    camac_event_time event_time;

    std::size_t event_index = 0;
};

