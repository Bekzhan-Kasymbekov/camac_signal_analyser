# CAMOC AE/EME Signal Reader and GUI Application - Project Context and Plan

I am interning at a science station and need to build an application for analysis and visualization of acoustic emission (AE) and electromagnetic emission (EME) signals from rock samples under stress/deformation.

Relevant uploaded files:
1. Technical task document: `Техническое задание практика 2026 (тема + программа).docx`
2. Writer/reader code document: `Write_Read.docx`

The technical task requires a program for processing signal forms of acoustic and electromagnetic emission. It includes reading an archive of AE/EME signals, building a GUI in Python and C/C++, plotting signals, FFT, wavelet scalograms, energy/power, b-value, Tsallis statistics, and other coefficients.

---

# 1. Main Goal

Build a reader/parser and GUI application for CAMOC/CAMAC binary signal archives.

The application should:

1. Read binary signal archives recorded by the CAMOC/CAMAC device.
2. Parse AE and EME/PHD signal events.
3. Visualize impulse accumulation graphs.
4. Allow cropping of the archive by selected time/event boundaries.
5. Display individual impulse windows.
6. Display AE and EME waveforms.
7. Display FFT / amplitude-frequency characteristics.
8. Calculate energy and power for AE and EME impulses.
9. Calculate total energy over the archive.
10. Calculate b-value using a Gutenberg-Richter style relation.
11. Calculate Tsallis q coefficient.
12. Calculate and display d-value, S-value, and gamma-value if formulas are confirmed.
13. Display wavelet scalograms for AE and EME.
14. Export processed catalogs, plots, and analysis results.

---

# 2. Technical Task Summary

The technical task says the application is for:

"Processing signal forms of acoustic and electromagnetic emission."

## Theoretical part

Need to review scientific literature about acoustic and electromagnetic emission of rocks in stressed/deformed states.

Suggested search/database tools:

- eLibrary
- Elicit
- Semantic Scholar
- Connected Papers

Suggested starting papers:

1. Klyuchkin, V. & Novikov, Victor & Okunev, V. & Zeigarnik, Vladimir. (2022).
   "Acoustic and electromagnetic emissions of rocks: insight from laboratory tests at press and shear machines."
   Environmental Earth Sciences. 81. 1-13.
   DOI: 10.1007/s12665-022-10189-z

2. Dumont S, de Bremond d’Ars J, Boulé J-B, Courtillot V, Gèze M, Gibert D, Kossobokov V, Le Mouël J-L, Lopes F, Neves MC, Silveira G, Petrosino S and Zuddas P. (2025).
   "On a planetary forcing of global seismicity."
   Front. Earth Sci. 13:1587650.
   DOI: 10.3389/feart.2025.1587650

## Practical part

The program must read an archive of acoustic and electromagnetic emission.

The GUI should have several windows.

---

# 3. GUI Requirements

## Window 1: Accumulation graphs and cropping

Requirements:

- Show two accumulation graphs in one graphical window:
  - AE impulse accumulation
  - EME impulse accumulation
- Allow cropping by selecting time boundaries of the whole archive.
- Further impulse processing must use the cropped archive/catalog.

Need to clarify what "накопление импульсов" means exactly:

1. Cumulative impulse count over time/event index?
2. Cumulative energy?
3. Cumulative amplitude?
4. Something else?

Initial safe implementation:

- x-axis: event index or event time
- y-axis: cumulative impulse count
- optional second mode: cumulative energy

## Window 2: Impulse viewer

Requirements:

Show 4 plots:

1. AE signal waveform
2. EME signal waveform
3. AE FFT / amplitude-frequency characteristic
4. EME FFT / amplitude-frequency characteristic

Also include:

- Input field for current impulse/window number.
- Display total number of impulse windows.
- Display currently shown impulse window number.
- Button for deleting the currently displayed impulse window.
- Deleted impulse should be excluded from the cropped catalog.
- Display energy and power of current AE impulse.
- Display energy and power of current EME impulse.
- Display sum of all AE impulse energies.
- Display sum of all EME impulse energies.

## Window 3: Coefficient plots

Requirements:

Show 4 graphical windows for coefficients:

1. d-value
2. S-value
3. gamma-value
4. Tsallis coefficient

For both AE and EME impulses.

Also include:

- Checkbox to calculate/display coefficients for all impulses in the archive.
- Checkbox to enable/disable moving window calculations.
- Input field for moving window point count.

Need to clarify formulas for:

- d-value
- S-value
- gamma-value
- Tsallis q

## Window 4: Wavelet scalograms

Requirements:

Show 2 graphical windows:

1. AE wavelet scalogram
2. EME wavelet scalogram

Need to clarify:

- Should wavelet scalograms be calculated for the current selected event?
- For all events?
- As a summary/average over all events?

Initial safe implementation:

- Display scalograms for the currently selected event.
- Add batch export later.

## Window 5: Export window

Requirements:

Export/save:

- Processed catalog
- Figures
- Tables
- Analysis results

Possible export formats:

- CSV for tables
- PNG/SVG for figures
- JSON for metadata
- NPZ/HDF5 for processed numerical arrays

---

# 4. Existing Writer and Reader Code

I have a document containing both:

1. C/C++ writing code, marked as `Write--ADC333(cpp)`
2. MATLAB reading code, marked as `Reader (m)`

The C writer records binary archives.
The MATLAB reader reads the binary archives.

---

# 5. Confirmed Binary Format

The writer code declares:

```cpp
short number = 3072;
short AE[3072], PHD[3072];
```

The writer writes each event like this:

```cpp
fwrite(&AE, sizeof(AE), 1, out);
fwrite(&PHD, sizeof(PHD), 1, out);
```

Therefore each event contains two arrays:

```text
AE[3072]  - short / uint16
PHD[3072] - short / uint16
```

Likely interpretation:

```text
AE  = acoustic emission channel
PHD = second channel, probably electromagnetic emission / EME
```

Each sample is 2 bytes.

Therefore:

```text
AE size per event  = 3072 * 2 = 6144 bytes
PHD size per event = 3072 * 2 = 6144 bytes

Total event size = 12288 bytes
```

The whole binary file layout is:

```text
Whole file
├── Event 0
│   ├── AE[3072]
│   └── PHD[3072]
│
├── Event 1
│   ├── AE[3072]
│   └── PHD[3072]
│
├── Event 2
│   ├── AE[3072]
│   └── PHD[3072]
│
└── ...
```

Parser validation:

```text
file_size % 12288 == 0
event_count = file_size / 12288
```

---

# 6. MATLAB Reader Logic

The MATLAB reader does:

```matlab
fid=fopen(FF,'rb');
[c,n]=fread(fid,'uint16');
fclose(fid);

kadr=1024;
kadr_a=3*kadr;
event=((n/(kadr_a*2)));
event_r=reshape(c,n/event,[]);
```

Since:

```text
kadr = 1024
kadr_a = 3 * 1024 = 3072
event = n / (3072 * 2)
```

This confirms:

```text
Each event contains 2 blocks of 3072 uint16 values.
Each event has 6144 uint16 values total.
Each event has 12288 bytes total.
```

Then MATLAB extracts AE:

```matlab
AE=event_r(13:(kadr_a),:);
AE_n=AE-mean(AE);
```

This means:

```text
MATLAB skips the first 12 values of the AE block.
MATLAB subtracts the mean from each AE event.
MATLAB currently plots only AE.
```

There is also a commented old line:

```matlab
% EMI=event_r((kadr_a+6):end,:);
```

This suggests:

```text
The second block after AE was probably intended as EMI/EME.
The MATLAB reader is incomplete for the current full task because it does not fully process EME.
```

---

# 7. Metadata Situation

The current active writer code overwrites the first 4 values of AE and PHD with time-like information:

```cpp
clock_gettime(CLOCK_REALTIME, &mt);
AE[0]=mt.tv_sec/1000000;
AE[1]=(mt.tv_sec/1000)%1000;
AE[2]=mt.tv_sec%1000;
AE[3]=mt.tv_nsec/1000000;

clock_gettime(CLOCK_REALTIME, &mt);
PHD[0]=mt.tv_sec/1000000;
PHD[1]=(mt.tv_sec/1000)%1000;
PHD[2]=mt.tv_sec%1000;
PHD[3]=mt.tv_nsec/1000000;
```

However, MATLAB has:

```matlab
Sys_info=event_r(1:8,:);
date_exp=event_r(9:12,:);
```

This may be from an older format, because the writer has an older metadata block commented out.

Important conclusion:

```text
The full event block is confirmed.
Metadata positions are not fully confirmed.
The safest parser should preserve raw AE and PHD arrays.
Processed signal arrays should skip metadata samples separately.
```

Suggested safe handling:

```text
AE raw block: 3072 values
PHD/EME raw block: 3072 values

Processed AE signal:
- Use AE[12..3071], matching MATLAB's AE=event_r(13:kadr_a,:)

Processed EME signal:
- Preserve full PHD raw block.
- Initially try PHD[12..3071] for symmetry.
- Also test PHD[4..3071] or PHD[5..3071] depending on supervisor/device info.
```

Important unresolved question:

```text
How many initial metadata values should be skipped for PHD/EME?
```

---

# 8. ADC and Signal Value Notes

The writer code masks samples with octal `07777`:

```cpp
AE[i]  = short(buf1[i]) & 07777;
PHD[i] = short(buf2[i]) & 07777;
```

Octal `07777` equals decimal `4095`.

Therefore:

```text
ADC is probably 12-bit.
Raw ADC range is probably 0..4095.
```

Possible signal normalization:

```text
Option 1:
signal = raw - mean(raw)

Option 2:
signal = raw - 2048

Option 3:
voltage = (raw - 2048) * voltage_range / 2048
```

The MATLAB reader currently uses mean subtraction:

```matlab
AE_n=AE-mean(AE);
```

So the first implementation should match MATLAB:

```text
processed_signal = raw_signal - mean(raw_signal)
```

The writer comments mention ranges:

```text
500 ns, +-4.096 V
500 ns, 1.024 V
```

Need to confirm exact voltage scaling with supervisor/station engineer.

---

# 9. Time Axis and CAMOC Tact Speed

I know that CAMOC treats time based on its tact speed.

The writer comments mention:

```text
500 ns
```

Therefore likely:

```text
1 sample = 1 tact
1 tact = 500 ns = 0.5 microseconds
sampling frequency = 1 / 500 ns = 2 MHz
```

For one full event:

```text
3072 samples * 500 ns = 1.536 ms
```

If using MATLAB's AE signal from index 13 onward:

```text
3060 samples * 500 ns = 1.530 ms
```

Important distinction:

```text
Absolute event time:
- When the impulse happened in the experiment/archive.
- Used for accumulation graphs and archive ordering.

Local signal time:
- Time inside one impulse window.
- Reconstructed from sample index and tact speed.
- Used for waveform plots, FFT, energy, power, wavelet scalograms.
```

Local time axis:

```text
time_seconds[i] = i * 500e-9
time_microseconds[i] = i * 0.5
```

FFT settings:

```text
sample_rate = 2,000,000 Hz
N = 3072
frequency_resolution = sample_rate / N = about 651 Hz
Nyquist frequency = sample_rate / 2 = 1 MHz
```

---

# 10. Recommended Technology Stack

Use a hybrid C++ and Python architecture.

## C++ core

Use C++ for:

1. Binary parser
2. Archive model
3. Event model
4. Fast signal processing if needed
5. Export of parsed data
6. Possibly FFT/statistics if performance matters

Recommended C++ tools:

```text
C++17 or C++20
CMake
pybind11
Catch2 or GoogleTest
optional: FFTW or KissFFT
optional: Eigen or xtensor
```

## Python GUI

Use Python for:

1. GUI
2. Interactive plotting
3. User controls
4. Cropping
5. Browsing/deleting impulses
6. Wavelet analysis
7. Export of figures/tables
8. Calling C++ parser through pybind11

Recommended Python libraries:

```text
PySide6 or PyQt6
pyqtgraph
numpy
scipy
pandas
PyWavelets
matplotlib only for static/export plots if needed
```

Recommended architecture:

```text
C++ parser/core -> pybind11 bindings -> Python GUI
```

Reason:

```text
C++ is good for reliable binary parsing and performance.
Python is much faster and easier for scientific GUI, plotting, FFT, wavelets, and prototyping.
```

---

# 11. Proposed Project Structure

```text
camoc_signal_analyzer/
├── cpp_core/
│   ├── CMakeLists.txt
│   ├── include/
│   │   ├── camoc_archive.hpp
│   │   ├── camoc_event.hpp
│   │   ├── camoc_parser.hpp
│   │   ├── signal_processing.hpp
│   │   └── statistics.hpp
│   ├── src/
│   │   ├── camoc_parser.cpp
│   │   ├── signal_processing.cpp
│   │   ├── statistics.cpp
│   │   └── bindings.cpp
│   └── tests/
│       ├── parser_tests.cpp
│       └── signal_tests.cpp
│
├── python_gui/
│   ├── main.py
│   ├── app_state.py
│   ├── windows/
│   │   ├── accumulation_window.py
│   │   ├── impulse_viewer_window.py
│   │   ├── coefficients_window.py
│   │   ├── wavelet_window.py
│   │   └── export_window.py
│   ├── widgets/
│   │   ├── signal_plot_widget.py
│   │   ├── fft_plot_widget.py
│   │   └── scalogram_widget.py
│   └── processing/
│       ├── fft.py
│       ├── energy.py
│       ├── wavelet.py
│       ├── b_value.py
│       └── tsallis.py
│
├── sample_data/
│   └── put_example_binary_files_here
│
├── docs/
│   ├── binary_format_notes.md
│   ├── formulas.md
│   └── user_manual.md
│
├── exports/
├── README.md
└── requirements.txt
```

---

# 12. Suggested C++ Data Structures

```cpp
#include <array>
#include <cstdint>
#include <vector>

constexpr std::size_t samples_per_channel = 3072;
constexpr double tact_seconds = 500e-9;
constexpr double sample_rate_hz = 1.0 / tact_seconds;

struct camoc_event {
    std::array<std::uint16_t, samples_per_channel> ae_raw{};
    std::array<std::uint16_t, samples_per_channel> eme_raw{};

    std::vector<double> ae_signal;
    std::vector<double> eme_signal;

    std::size_t event_index = 0;

    double event_time_seconds = 0.0;
    double tact_seconds_value = tact_seconds;
};

struct camoc_archive {
    std::vector<camoc_event> events;

    double tact_seconds_value = tact_seconds;
    double sample_rate_hz_value = sample_rate_hz;
};
```

---

# 13. Suggested Parser Constants

```cpp
constexpr std::size_t samples_per_channel = 3072;
constexpr std::size_t channels_per_event = 2;
constexpr std::size_t bytes_per_sample = sizeof(std::uint16_t);
constexpr std::size_t bytes_per_event =
    samples_per_channel * channels_per_event * bytes_per_sample;

constexpr double tact_seconds = 500e-9;
constexpr double sample_rate_hz = 1.0 / tact_seconds;
constexpr double full_event_duration_seconds =
    static_cast<double>(samples_per_channel) * tact_seconds;
```

Expected values:

```text
samples_per_channel = 3072
channels_per_event = 2
bytes_per_event = 12288
tact_seconds = 500e-9
sample_rate_hz = 2,000,000
full_event_duration_seconds = 0.001536 seconds
```

---

# 14. Minimal C++ Parser Milestone

First milestone should not be the full GUI.

First milestone:

```text
A C++ command-line parser that reads a CAMOC binary file and outputs:

- file size
- event count
- sample rate
- event duration
- first 10 raw AE values
- first 10 raw PHD/EME values
- first event AE CSV
- first event PHD/EME CSV
```

Minimal parser skeleton:

```cpp
#include <array>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

constexpr std::size_t samples_per_channel = 3072;
constexpr std::size_t channels_per_event = 2;
constexpr std::size_t bytes_per_sample = sizeof(std::uint16_t);
constexpr std::size_t bytes_per_event =
    samples_per_channel * channels_per_event * bytes_per_sample;

constexpr double tact_seconds = 500e-9;
constexpr double sample_rate_hz = 1.0 / tact_seconds;

struct camoc_event {
    std::array<std::uint16_t, samples_per_channel> ae_raw{};
    std::array<std::uint16_t, samples_per_channel> eme_raw{};
};

struct camoc_archive {
    std::vector<camoc_event> events;
};

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

camoc_archive parse_camoc_file(const std::string& file_path) {
    std::ifstream file(file_path, std::ios::binary);

    if (!file) {
        throw std::runtime_error("Could not open file: " + file_path);
    }

    const std::uint64_t file_size = get_file_size(file);

    if (file_size % bytes_per_event != 0) {
        throw std::runtime_error("Invalid file size. Not divisible by CAMOC event size.");
    }

    const std::size_t event_count = static_cast<std::size_t>(file_size / bytes_per_event);

    camoc_archive archive;
    archive.events.resize(event_count);

    for (std::size_t event_index = 0; event_index < event_count; ++event_index) {
        auto& event = archive.events[event_index];

        for (std::size_t i = 0; i < samples_per_channel; ++i) {
            event.ae_raw[i] = read_uint16_le(file);
        }

        for (std::size_t i = 0; i < samples_per_channel; ++i) {
            event.eme_raw[i] = read_uint16_le(file);
        }
    }

    return archive;
}

void solve() {
    const std::string file_path = "sample.001";

    const camoc_archive archive = parse_camoc_file(file_path);

    std::cout << "Events: " << archive.events.size() << '\n';
    std::cout << "Samples per channel: " << samples_per_channel << '\n';
    std::cout << "Sample rate: " << sample_rate_hz << " Hz\n";
    std::cout << "Event duration: "
              << samples_per_channel * tact_seconds * 1000.0
              << " ms\n";

    if (!archive.events.empty()) {
        const auto& first_event = archive.events.front();

        std::cout << "First 10 raw AE values:\n";
        for (std::size_t i = 0; i < 10; ++i) {
            std::cout << first_event.ae_raw[i] << '\n';
        }

        std::cout << "First 10 raw PHD/EME values:\n";
        for (std::size_t i = 0; i < 10; ++i) {
            std::cout << first_event.eme_raw[i] << '\n';
        }
    }
}

int main() {
    try {
        solve();
    } catch (const std::exception& error) {
        std::cerr << "Error: " << error.what() << '\n';
        return 1;
    }

    return 0;
}
```

---

# 15. Development Plan

## Stage 1: Confirm binary format

Goal:

Verify that the C++ parser reads the same data as MATLAB.

Tasks:

1. Get one real CAMOC binary file.
2. Check file size.
3. Confirm:

```text
file_size % 12288 == 0
```

4. Read the file using MATLAB.
5. Read the same file using C++.
6. Compare:
   - event count
   - first 10 raw AE values
   - first 10 raw PHD/EME values
   - first 10 processed AE values
   - AE min/max
   - PHD/EME min/max
   - plotted AE waveform

Success criteria:

```text
C++ event count matches MATLAB.
C++ raw AE values match MATLAB.
C++ AE waveform matches MATLAB plot.
```

## Stage 2: Minimal C++ parser CLI

Goal:

Create a command-line tool that reads a CAMOC binary file and prints useful summary information.

Features:

1. Open binary file.
2. Validate file size.
3. Calculate event count.
4. Read each event:
   - AE[3072]
   - PHD/EME[3072]
5. Print:
   - file size
   - event count
   - samples per channel
   - sample rate
   - event duration
   - first 10 AE values
   - first 10 PHD/EME values
6. Export first event as CSV:
   - first_event_ae.csv
   - first_event_eme.csv

## Stage 3: Basic signal processing

Goal:

Prepare signal arrays for plotting and analysis.

Tasks:

1. Implement mean subtraction:

```text
signal = raw - mean(raw)
```

2. Implement optional ADC-center subtraction:

```text
signal = raw - 2048
```

3. Implement time axis:

```text
time[i] = i * 500e-9
```

4. Implement event calculations:
   - min amplitude
   - max amplitude
   - peak-to-peak amplitude
   - energy
   - power

Possible formulas:

```text
energy = sum(signal[i]^2) * dt
power = energy / duration
dt = tact_seconds
duration = sample_count * tact_seconds
```

Need to clarify:

```text
Should energy be calculated using ADC counts or converted voltage?
```

## Stage 4: Minimal Python GUI

Goal:

Build the first usable GUI prototype.

Use:

```text
PySide6
pyqtgraph
numpy
```

Features:

1. Open binary file.
2. Call C++ parser or temporary Python parser.
3. Display number of events.
4. Show first event:
   - AE waveform
   - PHD/EME waveform
5. Add previous/next buttons.
6. Add event index input field.

Success criteria:

```text
User can open a file and browse impulse windows.
AE and EME/PHD waveforms display correctly.
```

## Stage 5: Window 1, accumulation and cropping

Goal:

Implement archive-level overview.

Features:

1. Plot AE accumulation graph.
2. Plot EME accumulation graph.
3. Show both in one graphical window.
4. Allow crop start/end selection.
5. Create cropped working catalog.
6. Further processing uses cropped catalog.

Important design rule:

```text
Never modify the original raw archive directly.
Keep:
1. original archive
2. cropped/working archive
3. deleted/ignored event list
```

## Stage 6: Window 2, impulse viewer

Goal:

Implement the main event inspection window.

Features:

1. Four plots:
   - AE waveform
   - EME waveform
   - AE FFT
   - EME FFT
2. Event number input.
3. Previous/next buttons.
4. Display:
   - total impulse windows
   - current impulse window number
   - AE energy
   - AE power
   - EME energy
   - EME power
   - total AE energy
   - total EME energy
5. Delete current impulse button.
6. Deleted impulse is excluded from cropped catalog.

FFT details:

```text
sample_rate = 2 MHz
frequency axis = fftfreq(N, dt)
show positive frequencies only
```

## Stage 7: b-value analysis

Goal:

Implement Gutenberg-Richter style b-value graph.

Formula:

```text
log10(N) = a - bM
```

Possible adaptation for AE/EME:

```text
M = log10(energy)
```

Steps:

1. Calculate energy for each event.
2. Convert energy to magnitude-like value:

```text
M = log10(energy)
```

3. Build cumulative distribution:

```text
N(M >= m)
```

4. Plot:

```text
x-axis = M
y-axis = log10(N)
```

5. Fit linear region.
6. b-value is negative slope.

Need to clarify:

```text
Exact definition of M.
Should b-value be calculated for AE only, EME only, both separately, or both combined?
What fitting range should be used?
```

## Stage 8: Window 3, coefficient plots

Goal:

Implement coefficient visualization.

Required coefficients:

```text
d-value
S-value
gamma-value
Tsallis q
```

Features:

1. Four plots.
2. Coefficients for current event or selected range.
3. Checkbox for all archive impulses.
4. Moving window checkbox.
5. Moving window size input.

Implementation approach:

```python
def calculate_d_value(events):
    pass

def calculate_s_value(events):
    pass

def calculate_gamma_value(events):
    pass

def calculate_tsallis_q(events):
    pass
```

Need to clarify formulas before implementing final version.

## Stage 9: Window 4, wavelet scalograms

Goal:

Add wavelet analysis.

Use:

```text
PyWavelets
numpy
pyqtgraph image display
```

Features:

1. AE scalogram.
2. EME scalogram.
3. Current event mode.
4. Optional batch export mode.

Initial implementation:

```text
Show scalogram for currently selected event.
```

Later:

```text
Batch export scalograms for all events.
```

## Stage 10: Window 5, export

Goal:

Allow saving processed results.

Export options:

1. Save cropped catalog.
2. Save figures.
3. Save CSV table with:
   - event index
   - AE energy
   - AE power
   - EME energy
   - EME power
   - max AE amplitude
   - max EME amplitude
   - b-value data
   - Tsallis q if calculated
4. Save selected event waveform.
5. Save FFT data.
6. Save scalogram images.

Possible formats:

```text
CSV for tables
PNG/SVG for figures
JSON for metadata
NPZ/HDF5 for arrays
```

---

# 16. Validation Strategy

At every stage, compare against MATLAB and simple known cases.

Minimum validation:

1. Event count matches MATLAB.
2. AE waveform matches MATLAB.
3. Mean-subtracted AE matches MATLAB `AE_n`.
4. FFT works on known test signal.
5. Energy calculation works on simple arrays:
   - all zeros
   - all ones
   - known sine wave
6. Cropping does not modify original archive.
7. Deleted events are excluded from calculations.
8. Exported CSV values are consistent with displayed GUI values.

---

# 17. Biggest Risks

1. Confusion between PHD and EME channel.
2. MATLAB reader may be outdated compared to writer code.
3. Metadata positions are unclear.
4. Exact voltage scaling is unclear.
5. Exact formulas for d-value, S-value, gamma-value, and Tsallis q need clarification.
6. Meaning of "accumulation graph" needs clarification.
7. Trying to build all GUI windows before parser is verified.
8. Interactive plotting may be slow if matplotlib is used instead of pyqtgraph.
9. Absolute event time reconstruction may be unreliable unless metadata is confirmed.

---

# 18. Questions to Ask Supervisor or Station Engineer

1. Is PHD definitely the electromagnetic emission channel?
2. How many metadata values should be skipped for AE?
3. How many metadata values should be skipped for PHD/EME?
4. Is the ADC always 12-bit, 0..4095?
5. What is the exact voltage range for AE?
6. What is the exact voltage range for EME/PHD?
7. Is tact speed always 500 ns?
8. What exactly does "накопление импульсов" mean?
   - cumulative count?
   - cumulative energy?
   - something else?
9. Are impulse windows already detected by the device?
10. Or do we need to detect impulses manually?
11. What are the exact formulas for:
   - d-value
   - S-value
   - gamma-value
   - Tsallis q
12. Should wavelet scalograms be generated:
   - for selected event?
   - for all events?
   - as a summary/average?
13. Should b-value be calculated:
   - for AE only?
   - for EME only?
   - for both separately?
   - for both combined?
14. Should energy/power be calculated using raw ADC counts or voltage-converted samples?

---

# 19. Immediate Next Steps

Do this first:

1. Get one small real CAMOC binary archive file.
2. Confirm:

```text
file_size % 12288 == 0
```

3. Write minimal C++ parser CLI.
4. Print event count.
5. Print first 10 AE values.
6. Print first 10 PHD/EME values.
7. Export first event AE and PHD/EME to CSV.
8. Plot exported CSV in Python.
9. Compare with MATLAB plot.
10. Only after parser is verified, start building GUI.

---

# 20. Recommended First Milestone

The first milestone should be:

```text
A working C++ command-line parser that reads one CAMOC binary file and outputs:

- file size
- event count
- sample rate
- event duration
- first 10 raw AE values
- first 10 raw PHD/EME values
- first event AE CSV
- first event PHD/EME CSV
```

This milestone proves the binary format is understood.

Only after that should the GUI be built.
