#include <arc/engine.hpp>
#include <algorithm>
#include <cctype>
#include <set>
namespace arc {
namespace j = boost::json;
std::string text(const j::value& value) {
    if (!value.is_string()) throw Invalid();
    return std::string(value.as_string());
}
j::array records(const j::value& value) {
    j::array rows;
    if (value.is_object()) rows.push_back(value);
    else if(value.is_array()) rows=value.as_array();
    else throw Invalid();
    if(rows.size()>MAX_ROWS) throw Invalid();
    for(const auto& row:rows) if(!row.is_object() || row.as_object().size()>MAX_COLS) throw Invalid();
    return rows;
}

} // namespace arc
