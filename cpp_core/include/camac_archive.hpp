#pragma once

#include "camac_event.hpp"
#include <vector>

struct camac_archive {
    std::vector<camac_event> events;
};
