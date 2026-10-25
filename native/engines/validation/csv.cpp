#include <arc/engine.hpp>
#include <algorithm>
#include <cctype>
#include <set>
namespace arc {
namespace j = boost::json;
std::vector<std::vector<std::string>> parse_csv(std::string data) {
    if(data.starts_with("\xef\xbb\xbf")) data.erase(0,3);
    std::vector<std::vector<std::string>> rows; std::vector<std::string> row; std::string field;
    bool quoted=false, closed=false, start=true;
    const auto end_field=[&](){row.push_back(field);field.clear();start=true;closed=false;if(row.size()>MAX_COLS)throw Invalid();};
    const auto end_row=[&](){end_field();rows.push_back(row);row.clear();if(rows.size()>MAX_ROWS+1)throw Invalid();};
    for(std::size_t i=0;i<data.size();++i){
        const char c=data[i];
        if(c=='\0') throw Invalid();
        if(quoted){
            if(c=='"'){
                if(i+1<data.size() && data[i+1]=='"'){field+='"';++i;}
                else {quoted=false;closed=true;}
            } else field+=c;
        } else if(c==',') end_field();
        else if(c=='\r' || c=='\n'){
            if(c=='\r' && i+1<data.size() && data[i+1]=='\n') ++i;
            end_row();
        } else if(c=='"') {
            if(!start || closed) throw Invalid();
            quoted=true;start=false;
        } else {
            if(closed) throw Invalid();
            field+=c;start=false;
        }
    }
    if(quoted) throw Invalid();
    if(!field.empty() || !row.empty() || closed || !start) end_row();
    if(rows.empty()) throw Invalid();
    return rows;
}
std::string csv_cell(std::string value) {
    // Spreadsheet formula protection is explicit and always enabled for CSV export.
    if(!value.empty() && (value[0]=='=' || value[0]=='+' || value[0]=='-' || value[0]=='@' || value[0]=='\t' || value[0]=='\r')) value="'"+value;
    std::string escaped="\"";
    for(char c:value){if(c=='"')escaped+='"';escaped+=c;}
    return escaped+'"';
}

} // namespace arc
