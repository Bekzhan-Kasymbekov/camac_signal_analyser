#include "camac_parser.hpp"

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <stdexcept>
#include <string>
#include <vector>
#include <cstdint>

namespace py = pybind11;

camac_encoding_format parse_encoding_format_string(const std::string& format_name) {
    if (format_name == "auto") {
        return camac_encoding_format::auto_detect;
    }
    
    if (format_name == "old_ae_header") {
        return camac_encoding_format::old_ae_header;
    }

    if (format_name == "new_channel_timestamps") {
        return camac_encoding_format::new_channel_timestamps;
    }

    throw std::runtime_error("Unknown CAMAC encoding format: " + format_name);
}

std::string get_encoding_format_name(const camac_archive& archive) {
    if (archive.encoding_format == camac_encoding_format::old_ae_header) {
        return "old_ae_header";
    }

    if (archive.encoding_format == camac_encoding_format::new_channel_timestamps) {
        return "new_channel_timestamps";
    }

    if (archive.encoding_format == camac_encoding_format::auto_detect) {
        return "auto_detect";
    }

    return "unknown";
}

std::size_t get_event_count(const camac_archive& archive) {
    return archive.events.size();
}

std::vector<double> get_relative_seconds(const camac_archive& archive) {
    std::vector<double> values;
    values.reserve(archive.events.size());

    for (const auto& event : archive.events) {
        values.push_back(event.event_time.relative_seconds);
    }

    return values;
}

std::vector<double> get_absolute_seconds(const camac_archive& archive) {
    std::vector<double> values;
    values.reserve(archive.events.size());

    for (const auto& event : archive.events) {
        values.push_back(event.event_time.absolute_seconds);
    }

    return values;
}

std::vector<int> get_time_valid_values(const camac_archive& archive) {
    std::vector<int> values;
    values.reserve(archive.events.size());

    for (const auto& event : archive.events) {
        values.push_back(event.event_time.is_valid ? 1 : 0);
    }

    return values;
}

std::vector<double> get_ae_max_abs_values(const camac_archive& archive) {
    std::vector<double> values;
    values.reserve(archive.events.size());

    for (const auto& event : archive.events) {
        values.push_back(calculate_max_abs(event.ae_signal));
    }

    return values;
}

std::vector<double> get_eme_max_abs_values(const camac_archive& archive) {
    std::vector<double> values;
    values.reserve(archive.events.size());

    for (const auto& event : archive.events) {
        values.push_back(calculate_max_abs(event.eme_signal));
    }

    return values;
}

std::vector<double> get_ae_energy_values(const camac_archive& archive) {
    std::vector<double> values;
    values.reserve(archive.events.size());

    for (const auto& event : archive.events) {
        values.push_back(calculate_energy(event.ae_signal));
    }

    return values;
}

std::vector<double> get_eme_energy_values(const camac_archive& archive) {
    std::vector<double> values;
    values.reserve(archive.events.size());

    for (const auto& event : archive.events) {
        values.push_back(calculate_energy(event.eme_signal));
    }

    return values;
}

std::vector<std::uint16_t> get_ae_raw(
    const camac_archive& archive,
    std::size_t event_index
) {
    if (event_index >= archive.events.size()) {
        throw std::runtime_error("Event index is out of range");
    }

    const auto& raw = archive.events[event_index].ae_raw;

    return std::vector<std::uint16_t>(raw.begin(), raw.end());
}

std::vector<std::uint16_t> get_eme_raw(
    const camac_archive& archive,
    std::size_t event_index
) {
    if (event_index >= archive.events.size()) {
        throw std::runtime_error("Event index is out of range");
    }

    const auto& raw = archive.events[event_index].eme_raw;

    return std::vector<std::uint16_t>(raw.begin(), raw.end());
}

std::vector<double> get_ae_signal(const camac_archive& archive, std::size_t event_index) {
    if (event_index >= archive.events.size()) {
        throw std::runtime_error("Event index is out of range");
    }

    return archive.events[event_index].ae_signal;
}

std::vector<double> get_eme_signal(const camac_archive& archive, std::size_t event_index) {
    if (event_index >= archive.events.size()) {
        throw std::runtime_error("Event index is out of range");
    }

    return archive.events[event_index].eme_signal;
}

py::dict get_event_info(const camac_archive& archive, std::size_t event_index) {
    if (event_index >= archive.events.size()) {
        throw std::runtime_error("Event index is out of range");
    }

    const auto& event = archive.events[event_index];

    py::dict info;
    info["event_index"] = event.event_index;
    info["time_valid"] = event.event_time.is_valid;
    info["absolute_seconds"] = event.event_time.absolute_seconds;
    info["relative_seconds"] = event.event_time.relative_seconds;
    info["ae_max_abs"] = calculate_max_abs(event.ae_signal);
    info["eme_max_abs"] = calculate_max_abs(event.eme_signal);
    info["ae_energy"] = calculate_energy(event.ae_signal);
    info["eme_energy"] = calculate_energy(event.eme_signal);

    return info;
}

camac_archive parse_camac_file_for_python(
    const std::string& file_path
) {
    return parse_camac_file(file_path);
}

PYBIND11_MODULE(camac_core, module) {
    module.doc() = "CAMAC binary parser core";

    py::class_<camac_archive>(module, "CamacArchive")
        .def("encoding_format", &get_encoding_format_name)
        .def("event_count", &get_event_count)
        .def("relative_seconds", &get_relative_seconds)
        .def("absolute_seconds", &get_absolute_seconds)
        .def("time_valid_values", &get_time_valid_values)
        .def("ae_max_abs_values", &get_ae_max_abs_values)
        .def("eme_max_abs_values", &get_eme_max_abs_values)
        .def("ae_energy_values", &get_ae_energy_values)
        .def("eme_energy_values", &get_eme_energy_values)
        .def("ae_raw", &get_ae_raw)
        .def("eme_raw", &get_eme_raw)
        .def("ae_signal", &get_ae_signal)
        .def("eme_signal", &get_eme_signal)
        .def("event_info", &get_event_info);

    module.def(
        "parse_camac_file",
        &parse_camac_file_for_python,
        py::arg("file_path")
    );
}
