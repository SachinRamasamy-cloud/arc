#pragma once
#include <boost/json.hpp>
#include <cstddef>
#include <stdexcept>
#include <string>
#include <vector>
namespace arc {
namespace json = boost::json;
inline constexpr std::size_t MAX_BYTES=16'000'000;
inline constexpr std::size_t MAX_ROWS=100'000;
inline constexpr std::size_t MAX_COLS=128;
struct Invalid : std::runtime_error { Invalid():std::runtime_error("invalid") {} };
std::string text(const json::value& value);
std::string trim(std::string s);
json::array records(const json::value& value);
std::vector<std::vector<std::string>> parse_csv(std::string data);
std::string csv_cell(std::string value);
json::object process(const json::object& request);
}
