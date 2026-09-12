// Compile the actual pinned Create/ReleaseResourceContext bodies. EGL and the
// reactor are adapters; run the virtual guest separately for real context proof.
#include <functional>
#include <iostream>
#include <memory>
#include <string>
#include <thread>

static int errors = 0;
struct Log {
  template <class T> Log& operator<<(const T&) { return *this; }
};
#define FML_LOG(level) (++errors, Log{})
#define FML_DLOG(level) Log{}
struct GrDirectContext {};
template <class T> using sk_sp = std::shared_ptr<T>;
struct Worker {
  bool allowed = false;
  void SetReactionsAllowedOnCurrentThread(bool value) { allowed = value; }
};
struct EmbedderSurface {
  virtual ~EmbedderSurface() = default;
  virtual void ReleaseResourceContext() const {}
};
struct EmbedderSurfaceGLImpeller : EmbedderSurface {
  struct Dispatch {
    std::function<bool()> gl_make_resource_current_callback;
    std::function<bool()> gl_clear_current_callback;
  } gl_dispatch_table_;
  std::shared_ptr<Worker> worker_ = std::make_shared<Worker>();
  mutable bool resource_context_current_ = false;
  sk_sp<GrDirectContext> CreateResourceContext() const;
  // @SURFACE_DECL@
};
struct PlatformViewEmbedder {
  EmbedderSurface* embedder_surface_ = nullptr;
  void ReleaseResourceContext() const;
};
// @METHODS@

int main(int argc, char** argv) {
  if (argc != 2) return 2;
  const std::string mode = argv[1];
  bool pass = false;
  // Match the engine contract: both methods execute on the IO thread.
  std::thread io([&] {
    EmbedderSurfaceGLImpeller surface;
    PlatformViewEmbedder view{&surface};
    bool current = false;
    bool fail_clear = mode == "clear-failure";
    int clears = 0;
    const auto owner = std::this_thread::get_id();
    surface.gl_dispatch_table_.gl_make_resource_current_callback = [&] {
      if (mode == "bind-failure") return false;
      current = true;
      return true;
    };
    surface.gl_dispatch_table_.gl_clear_current_callback = [&] {
      ++clears;
      if (surface.worker_->allowed || std::this_thread::get_id() != owner)
        std::abort();
      if (fail_clear) return false;
      current = false;
      return true;
    };
    if (mode == "null-surface") {
      view.embedder_surface_ = nullptr;
      view.ReleaseResourceContext();
      pass = clears == 0 && errors == 0;
      return;
    }
    surface.CreateResourceContext();
    if (mode == "repeated-bind") surface.CreateResourceContext();
    view.ReleaseResourceContext();
    if (mode == "clear-failure") {
      pass = current && clears == 1 && errors == 1 &&
             surface.resource_context_current_ && !surface.worker_->allowed;
      fail_clear = false;
      view.ReleaseResourceContext();
      pass = pass && !current && clears == 2 &&
             !surface.resource_context_current_;
    } else if (mode == "bind-failure") {
      pass = !current && clears == 0 && !surface.worker_->allowed && errors == 0;
    } else {
      pass = !current && clears == 1 && !surface.worker_->allowed && errors == 0;
      view.ReleaseResourceContext();
      pass = pass && clears == 1;  // No double release after successful clear.
    }
  });
  io.join();
  std::cout << mode << ": " << (pass ? "PASS" : "FAIL") << '\n';
  return pass ? 0 : 1;
}
