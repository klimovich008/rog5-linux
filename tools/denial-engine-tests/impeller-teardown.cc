// Compile the actual patched destructor with narrow context/resource adapters.
#include <iostream>
#include <memory>
#include <sstream>
#include <string>
#include <vector>
static std::vector<std::string> calls;
static bool current;
static bool released_without_current;
static int errors;
struct ErrorLog {
  template<class T> ErrorLog& operator<<(const T&) { return *this; }
  ~ErrorLog() { ++errors; }
};
#define FML_LOG(level) ErrorLog()
struct GLContextResult { bool result; bool GetResult() { return result; } };
struct GPUSurfaceGLDelegate {
  bool bind_ok=true, clear_ok=true;
  std::unique_ptr<GLContextResult> GLContextMakeCurrent() {
    calls.push_back("bind"); if(bind_ok) current=true;
    return std::make_unique<GLContextResult>(GLContextResult{bind_ok});
  }
  bool GLContextClearCurrent() {
    calls.push_back("clear"); if(clear_ok) current=false; return clear_ok;
  }
};
struct Resource {
  std::string name;
  explicit Resource(std::string value):name(std::move(value)) {}
  ~Resource() { calls.push_back(name); if(!current) released_without_current=true; }
};
class GPUSurfaceGLImpeller {
 public:
  GPUSurfaceGLDelegate* delegate_;
  std::shared_ptr<Resource> impeller_context_;
  std::shared_ptr<Resource> aiks_context_;
  bool is_valid_;
  explicit GPUSurfaceGLImpeller(GPUSurfaceGLDelegate* d,bool valid=true):delegate_(d),is_valid_(valid) {
    if(valid) { impeller_context_=std::make_shared<Resource>("context");aiks_context_=std::make_shared<Resource>("aiks"); }
  }
  ~GPUSurfaceGLImpeller();
};
// @DESTRUCTOR@
int main(int argc,char** argv) {
  if(argc!=2) return 2;
  const std::string mode=argv[1]; GPUSurfaceGLDelegate delegate;
  current=mode!="initially-unbound";
  delegate.bind_ok=mode!="bind-failure";
  delegate.clear_ok=mode!="clear-failure";
  { GPUSurfaceGLImpeller surface(&delegate,mode!="invalid"); }
  bool ok=false;
  if(mode=="invalid") ok=calls.empty() && errors==0;
  else if(mode=="bind-failure") ok=errors==1 && calls.front()=="bind" && current &&
      calls==std::vector<std::string>({"bind","aiks","context"});
  else if(mode=="clear-failure") ok=errors==1 && current && !released_without_current &&
      calls==std::vector<std::string>({"bind","aiks","context","clear"});
  else if(mode=="normal" || mode=="initially-unbound") ok=errors==0 && !current && !released_without_current &&
      calls==std::vector<std::string>({"bind","aiks","context","clear"});
  std::cout<<(ok?"PASS ":"FAIL ")<<mode<<"\n";return ok?0:1;
}
