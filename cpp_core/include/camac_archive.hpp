#pragma once

#include "camac_event.hpp"
#include <vector>

struct camac_archive {
    std::vector<camac_event> events;
    camac_encoding_format encoding_format = camac_encoding_format::auto_detect;
};
