#include <arc/engine.hpp>
#include <algorithm>
#include <cctype>
#include <set>
namespace arc {
namespace j = boost::json;
j::object process(const j::object& req) {
    const auto op=text(req.at("operation"));
    const auto& data=req.at("data");
    j::value output;std::size_t count=0;std::string format="json";
    if(op=="csv_to_json"){
        const auto rows=parse_csv(text(data));
        const auto& header=rows.front(); std::set<std::string> names;
        for(const auto& name:header) if(name.empty() || !names.insert(name).second) throw Invalid();
        j::array result;
        for(std::size_t i=1;i<rows.size();++i){
            if(rows[i].size()!=header.size()) throw Invalid();
            j::object row;
            for(std::size_t k=0;k<header.size();++k) row[header[k]]=rows[i][k];
            result.push_back(row);
        }
        count=result.size();output=result;
    } else {
        auto rows=records(data);count=rows.size();
        j::array required;
        if(const auto* fields=req.if_contains("required_fields")){
            if(!fields->is_array()) { throw Invalid(); }
            required=fields->as_array();
        }
        for(const auto& row:rows)for(const auto& field:required){
            const auto name=text(field);const auto* v=row.as_object().if_contains(name);
            if(!v || v->is_null())throw Invalid();
        }
        if(op=="validate") output=rows;
        else if(op=="normalize"){
            j::object mappings;
            if(const auto* m=req.if_contains("mappings")){if(!m->is_object())throw Invalid();mappings=m->as_object();}
            std::set<std::string> lowercase;
            if(const auto* lower=req.if_contains("lowercase")){
                if(!lower->is_array()) { throw Invalid(); }
                for(const auto& v:lower->as_array()) lowercase.insert(text(v));
            }
            j::array result;
            for(const auto& r:rows){
                j::object row;
                for(const auto& field:r.as_object()){
                    std::string name(field.key());if(const auto* mapped=mappings.if_contains(name))name=text(*mapped);
                    if(name.empty() || row.contains(name))throw Invalid();
                    j::value value=field.value();
                    if(value.is_string()){
                        auto s=trim(text(value));
                        if(lowercase.contains(name))std::transform(s.begin(),s.end(),s.begin(),[](unsigned char c){return c<128?static_cast<char>(std::tolower(c)):static_cast<char>(c);});
                        value=s;
                    }
                    row[name]=value;
                }
                result.push_back(row);
            }
            output=result;
        } else if(op=="json_to_csv"){
            std::set<std::string> names;
            for(const auto& row:rows)for(const auto& field:row.as_object())names.insert(std::string(field.key()));
            if(names.empty() || names.size()>MAX_COLS)throw Invalid();
            std::string csv;bool first=true;
            for(const auto& name:names){if(!first) { csv+=','; }
                    first=false;csv+=csv_cell(name);}csv+="\r\n";
            for(const auto& row:rows){
                first=true;
                for(const auto& name:names){
                    if(!first) { csv+=','; }
                    first=false;
                    const auto* value=row.as_object().if_contains(name);
                    if(!value || value->is_null())csv+=csv_cell("");
                    else if(value->is_string())csv+=csv_cell(text(*value));
                    else if(value->is_object() || value->is_array())throw Invalid();
                    else csv+=csv_cell(j::serialize(*value));
                }
                csv+="\r\n";
                if(csv.size()>MAX_BYTES)throw Invalid();
            }
            output=csv;format="csv";
        }else throw Invalid();
    }
    return {{"ok",true},{"engine_version","1.0.0"},{"records",count},{"format",format},{"output",output}};
}

} // namespace arc
