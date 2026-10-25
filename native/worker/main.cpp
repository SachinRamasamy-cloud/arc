#include <arc/engine.hpp>
#include <iostream>
#include <string>
namespace j = boost::json;
using namespace arc;
int main(int argc,char** argv){
    if(argc==2 && std::string(argv[1])=="--version"){std::cout<<"arc-engine 1.0.0\n";return 0;}
    try{
        std::string input;char buffer[8192];
        while(std::cin){std::cin.read(buffer,sizeof buffer);input.append(buffer,static_cast<std::size_t>(std::cin.gcount()));if(input.size()>MAX_BYTES)throw Invalid();}
        j::parse_options options;options.max_depth=64;
        boost::system::error_code ec;
        auto value=j::parse(input,ec,{},options);
        if(ec || !value.is_object())throw Invalid();
        auto result=process(value.as_object());const auto encoded=j::serialize(result);
        if(encoded.size()>MAX_BYTES)throw Invalid();
        std::cout<<encoded<<'\n';return 0;
    }catch(...){std::cout<<"{\"ok\":false,\"code\":\"INVALID_INPUT\"}\n";return 2;}
}
