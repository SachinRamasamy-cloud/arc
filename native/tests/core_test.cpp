#include <arc/engine.hpp>
#include <stdexcept>
#include <string>
namespace {
void require(bool condition) { if (!condition) throw std::runtime_error("Native core regression failed"); }
}
int main(){
 using namespace arc;
 require(trim(" \tAda Lovelace\r\n") == "Ada Lovelace");
 auto csv = parse_csv("name,email\r\nAda,a@example.test\r\n");
 require(csv.size()==2 && csv[1][0]=="Ada");
 bool rejected = false;
 try { parse_csv("a,b\r\n\"not closed,other"); } catch(const Invalid&) { rejected=true; }
 require(rejected);
 json::object req;
 req["operation"]="normalize";
 req["data"]=json::array{json::object{{"email"," ADA@EXAMPLE.TEST "}}};
 req["lowercase"]=json::array{"email"};
 auto result=process(req);
 require(result.at("ok").as_bool());
 auto output=result.at("output").as_array();
 require(output.at(0).as_object().at("email").as_string()=="ada@example.test");
 return 0;
}
