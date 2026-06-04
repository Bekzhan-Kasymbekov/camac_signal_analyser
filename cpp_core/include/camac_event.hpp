#pragma once

#include <array>
#include <cstdint>
#include <cstddef>

constexpr std::size_t samples_per_channel = 3072;
constexpr std::size_t channels_per_event = 2;
constexpr std::size_t bytes_per_sample = sizeof(std::uint16_t);

constexpr std::size_t bytes_per_event =
    samples_per_channel * channels_per_event * bytes_per_sample;

constexpr double tact_seconds = 500e-9;
constexpr double sample_rate_hz = 1.0 / tact_seconds;

struct camac_event {
    std::array<std::uint16_t, samples_per_channel> ae_raw{};
    std::array<std::uint16_t, samples_per_channel> eme_raw{};
};
