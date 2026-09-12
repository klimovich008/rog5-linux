// The runner inserts the production diagnostic helper; logging is an adapter.
#include <algorithm>
#include <atomic>
#include <cassert>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <mutex>
#include <sstream>
#include <string>
#include <thread>
#include <vector>
std::mutex log_mutex;
std::vector<std::string> logs;
struct Log {
  std::ostringstream text;
  template<class T> Log& operator<<(T value) { text << value; return *this; }
  ~Log() { std::lock_guard<std::mutex> guard(log_mutex); logs.push_back(text.str()); }
};
namespace fml { constexpr int kLogInfo = 0; constexpr int kLogError = 2; }
struct { bool verbose_logging = false; } settings;
struct { int min_log_level = 0; } log_settings;
constexpr int INFO = 0;
constexpr int IMPORTANT = 3;
#define FML_LOG(level) if ((level) < log_settings.min_log_level) {} else Log{}
// @HELPER@
int main(int argc, char** argv) {
  assert(argc == 2);
  const std::string mode = argv[1];
  // @LOG_THRESHOLD@
  setenv("DENIA_RENDER_AUDIT", mode == "disabled" ? "0" : "1", 1);
  using namespace denial_render_audit;
  if (mode == "disabled") {
    Scope scope("disabled"); Record("probe");
    assert(events == 0 && calls == 0 && logs.empty() && current.id == 0);
  } else if (mode == "nested") {
    {
      Scope outer("retained-output"); const auto id = current.id;
      { Scope inner("framework-pipeline"); assert(current.id != id); }
      assert(current.id == id && std::strcmp(current.origin, "retained-output") == 0);
      Record("surface-begin", 3, 1, 9);
    }
    assert(current.id == 0 && std::strcmp(current.origin, "unscoped") == 0);
    assert(logs.size() == 5 && logs[3].find("call=1 origin=retained-output stage=surface-begin view=3 value=1 generation=9") != std::string::npos);
  } else if (mode == "concurrent-cap") {
    std::vector<std::thread> workers;
    for (int i = 0; i < 4; ++i) workers.emplace_back([] {
      for (int j = 0; j < 2000; ++j) {
        { Scope scope("worker"); Record("probe"); }
        assert(current.id == 0);
      }
    });
    for (auto& worker : workers) worker.join();
    assert(events == kLimit && calls == kLimit && logs.size() == kLimit);
    std::vector<unsigned> sequences;
    unsigned cap_markers = 0;
    for (const auto& line : logs) {
      sequences.push_back(std::stoul(line.substr(line.find("seq=") + 4)));
      cap_markers += line.find("cap_last=1") != std::string::npos;
    }
    std::sort(sequences.begin(), sequences.end());
    for (unsigned i = 0; i < kLimit; ++i) assert(sequences[i] == i + 1);
    assert(cap_markers == 1 && current.id == 0);
  } else { return 2; }
}
