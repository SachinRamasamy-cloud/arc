#include <arc/engine.hpp>
#include <algorithm>
#include <cctype>
#include <set>
namespace arc {
namespace j = boost::json;
std::string trim(std::string s) {
    const auto whitespace=[](unsigned char c){ return c==' ' || c=='\t' || c=='\r' || c=='\n'; };
    while(!s.empty() && whitespace(static_cast<unsigned char>(s.back()))) s.pop_back();
    const auto start=std::find_if_not(s.begin(),s.end(),whitespace);
    s.erase(s.begin(),start); return s;
}

} // namespace arc
