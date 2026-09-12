// Adapter-only fixture. Markers are replaced with exact pinned engine source.
// This characterizes queue ordering; it does not implement a reservation fix.
#include <atomic>
#include <cassert>
#include <condition_variable>
#include <cstdint>
#include <deque>
#include <functional>
#include <iostream>
#include <memory>
#include <mutex>
#include <optional>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

template <typename... T> void Trace(const T&...) {}
#define TRACE_EVENT0(...) Trace(__VA_ARGS__)
#define TRACE_EVENT_ASYNC_BEGIN0(...) Trace(__VA_ARGS__)
#define TRACE_EVENT_ASYNC_BEGIN0_WITH_FLOW_IDS(...) Trace(__VA_ARGS__)
#define TRACE_EVENT_ASYNC_END0(...) Trace(__VA_ARGS__)
#define TRACE_FLOW_BEGIN(...) Trace(__VA_ARGS__)
#define TRACE_FLOW_END(...) Trace(__VA_ARGS__)
#define TRACE_FLOW_STEP(...) Trace(__VA_ARGS__)
#define TRACE_EVENT_WITH_FRAME_NUMBER(...) Trace(__VA_ARGS__)
#define FML_TRACE_COUNTER(...) Trace(__VA_ARGS__)
#define FML_CHECK(value) assert(value)
#define FML_DCHECK(value) assert(value)
#define FML_DLOG(level) std::cerr
#define FML_DISALLOW_COPY_AND_ASSIGN(T) T(const T&) = delete; T& operator=(const T&) = delete

namespace fml {
struct TimeDelta {
  int64_t value = 0;
  static TimeDelta FromMicroseconds(int64_t value) { return {value}; }
  static TimeDelta FromMilliseconds(int64_t value) { return {value * 1000}; }
  bool operator>(TimeDelta other) const { return value > other.value; }
  TimeDelta operator+(TimeDelta other) const { return {value + other.value}; }
};
struct TimePoint {
  static TimePoint Now() { return {}; }
  TimeDelta ToEpochDelta() const { return {}; }
};
class Semaphore {
 public:
  explicit Semaphore(int count) : count_(count) {}
  bool TryWait() { if (count_ == 0) return false; --count_; return true; }
  void Signal() { ++count_; }
  bool IsValid() const { return true; }
 private:
  int count_;
};
template <class T> struct WeakFactory {
  T* pointer;
  T* GetWeakPtr() const { return pointer; }
};
template <class T> T MakeCopyable(T closure) { return closure; }
}  // namespace fml

int64_t Dart_TimelineGetMicros() { return 0; }
const fml::TimeDelta kNotifyIdleTaskWaitTime = fml::TimeDelta::FromMilliseconds(51);

struct TaskRunner {
  std::deque<std::function<void()>> ready;
  std::vector<std::function<void()>> delayed;
  void PostTask(std::function<void()> task) { ready.push_back(std::move(task)); }
  void PostDelayedTask(std::function<void()> task, fml::TimeDelta) {
    delayed.push_back(std::move(task));
  }
  bool RunsTasksOnCurrentThread() const { return true; }
  void Drain() {
    size_t count = 0;
    while (!ready.empty()) {
      if (++count > 20) throw std::runtime_error("unexpected unbounded reposting");
      auto task = std::move(ready.front());
      ready.pop_front();
      task();
    }
  }
};
struct TaskRunners {
  TaskRunner* ui;
  TaskRunner* raster;
  TaskRunner* GetUITaskRunner() const { return ui; }
  TaskRunner* GetRasterTaskRunner() const { return raster; }
};

namespace flutter {
// @PIPELINE@
size_t GetNextPipelineTraceID() { static size_t id = 0; return ++id; }
struct LayerTree {};
struct FrameTimingsRecorder {
  explicit FrameTimingsRecorder(uint64_t id = 0) : number(id) {}
  uint64_t number;
  void RecordBuildStart(fml::TimePoint) {}
  void RecordBuildEnd(fml::TimePoint) {}
  void RecordVsync(fml::TimePoint, fml::TimePoint) {}
  fml::TimePoint GetVsyncTargetTime() const { return {}; }
  uint64_t GetFrameNumber() const { return number; }
};
struct LayerTreeTask {
  LayerTreeTask(int64_t id, std::unique_ptr<LayerTree>, float) : view_id(id) {}
  int64_t view_id;
  std::optional<std::unordered_set<int64_t>> dirty_texture_ids;
};
// @FRAME_ITEM@

enum class DrawStatus { kYielded, kPipelineEmpty, kDone };
enum class DoDrawStatus { kDone, kEnqueuePipeline };
struct ThreadMerger { bool IsOnRasterizingThread() const { return true; } };
struct ExternalViewEmbedder {
  bool GetUsedThisFrame() const { return false; }
  void SetUsedThisFrame(bool) {}
  void EndFrame(bool, const std::shared_ptr<ThreadMerger>&) {}
};
struct RasterDelegate {
  TaskRunners runners;
  const TaskRunners& GetTaskRunners() const { return runners; }
};
struct Rasterizer {
  struct DoDrawResult {
    DoDrawStatus status = DoDrawStatus::kDone;
    std::unique_ptr<FrameItem> resubmitted_item;
  };
  Rasterizer(TaskRunners runners, std::vector<std::string>& events)
      : delegate_{runners}, events_(events), weak_factory_{this} {}
  Rasterizer* GetWeakPtr() { return this; }
  DrawStatus Draw(const std::shared_ptr<FramePipeline>& pipeline);
  bool ShouldResubmitFrame(const DoDrawResult& result);
  DrawStatus ToDrawStatus(DoDrawStatus) { return DrawStatus::kDone; }
  DoDrawResult DoDraw(std::unique_ptr<FrameTimingsRecorder> recorder,
                      std::vector<std::unique_ptr<LayerTreeTask>> tasks) {
    assert(!tasks.empty());
    events_.push_back("draw:" + std::to_string(recorder->number));
    if (resubmissions_remaining > 0) {
      --resubmissions_remaining;
      return {.status = DoDrawStatus::kDone,
              .resubmitted_item = std::make_unique<FrameItem>(
                  std::move(tasks), std::move(recorder))};
    }
    return {};
  }
  unsigned resubmissions_remaining = 0;
  RasterDelegate delegate_;
  std::vector<std::string>& events_;
  fml::WeakFactory<Rasterizer> weak_factory_;
  std::shared_ptr<ThreadMerger> raster_thread_merger_;
  std::unique_ptr<ExternalViewEmbedder> external_view_embedder_;
  std::unordered_set<int64_t> pending_texture_ids_;
};
// @DRAW@
// @RESUBMIT@

struct Shell {
  Shell(TaskRunners runners, Rasterizer* rasterizer)
      : task_runners_(runners), rasterizer_(rasterizer) {}
  void OnAnimatorDraw(std::shared_ptr<FramePipeline> pipeline);
  void OnAnimatorBeginFrame(fml::TimePoint, uint64_t) {
    ++framework_callbacks;
    framework_callback();
  }
  void OnAnimatorUpdateLatestFrameTargetTime(fml::TimePoint) {}
  void OnAnimatorNotifyIdle(fml::TimeDelta) {}
  std::function<void()> framework_callback = [] {};
  unsigned framework_callbacks = 0;
  bool is_set_up_ = true;
  TaskRunners task_runners_;
  Rasterizer* rasterizer_;
  std::atomic<bool> waiting_for_first_frame_{false};
  std::condition_variable waiting_for_first_frame_condition_;
};
// @SHELL_DRAW@

struct Animator {
  Animator(Shell& shell, TaskRunners runners)
      : delegate_(shell), task_runners_(runners), weak_factory_{this} {}
  void BeginFrame(std::unique_ptr<FrameTimingsRecorder> recorder);
  void EndFrame();
  void Render(int64_t, std::unique_ptr<LayerTree>, float);
  void OnAllViewsRendered();
  // Observe the source's retry decision without adapting another vsync cycle.
  void RequestFrame() { ++retry_requests; }
  unsigned retry_requests = 0;
  Shell& delegate_;
  TaskRunners task_runners_;
  fml::WeakFactory<Animator> weak_factory_;
  std::shared_ptr<FramePipeline> layer_tree_pipeline_ = std::make_shared<FramePipeline>(2);
  FramePipeline::ProducerContinuation producer_continuation_;
  std::unique_ptr<FrameTimingsRecorder> frame_timings_recorder_;
  std::unordered_map<int64_t, std::unique_ptr<LayerTreeTask>> layer_trees_tasks_;
  std::deque<uint64_t> trace_flow_ids_;
  uint64_t frame_request_number_ = 0;
  bool frame_scheduled_ = false;
  bool regenerate_layer_trees_ = true;
  bool has_rendered_ = false;
  fml::Semaphore pending_frame_semaphore_{0};
  fml::TimeDelta dart_frame_deadline_;
};
// @BEGIN_FRAME@
// @END_FRAME@
// @RENDER@
// @ALL_VIEWS@
}  // namespace flutter

struct Fixture {
  TaskRunner ui, raster;
  TaskRunners runners{&ui, &raster};
  std::vector<std::string> events;
  flutter::Rasterizer rasterizer{runners, events};
  flutter::Shell shell{runners, &rasterizer};
  flutter::Animator animator{shell, runners};

  void Begin(uint64_t id, bool render = true, bool early_end = false) {
    shell.framework_callback = [this, render, early_end] {
      if (render) animator.Render(1, std::make_unique<flutter::LayerTree>(), 1.0f);
      if (early_end) animator.OnAllViewsRendered();
    };
    animator.BeginFrame(std::make_unique<flutter::FrameTimingsRecorder>(id));
    events.push_back("begin-return:" + std::to_string(id));
  }
  void End(uint64_t id) {
    animator.EndFrame();
    events.push_back("end-return:" + std::to_string(id));
  }
  void Barrier() { raster.PostTask([this] { events.push_back("barrier"); }); }
  void Expect(std::initializer_list<std::string> expected) {
    for (const auto& event : events) std::cout << event << '\n';
    if (events != std::vector<std::string>(expected))
      throw std::runtime_error("unexpected event order");
  }
};

int main(int argc, char** argv) {
  if (argc != 2) return 2;
  const std::string mode = argv[1];
  Fixture f;
  if (mode == "single-item") {
    f.Begin(1); f.End(1); f.Barrier(); f.raster.Drain();
    f.Expect({"begin-return:1", "end-return:1", "draw:1", "barrier"});
  } else if (mode == "queued-item-barrier") {
    f.Begin(1); f.End(1); f.Begin(2); f.End(2);
    if (f.raster.ready.size() != 1) throw std::runtime_error("second item posted a draw");
    f.Barrier(); f.raster.Drain();
    f.Expect({"begin-return:1", "end-return:1", "begin-return:2", "end-return:2",
              "draw:1", "barrier", "draw:2"});
  } else if (mode == "begin-return-barrier") {
    // Only one view rendered: the runtime's all-views early EndFrame is absent.
    f.Begin(1); f.Barrier(); f.End(1); f.raster.Drain();
    f.Expect({"begin-return:1", "end-return:1", "barrier", "draw:1"});
  } else if (mode == "zero-render") {
    f.Begin(1, false); f.End(1);
    if (!f.raster.ready.empty()) throw std::runtime_error("empty frame posted draw");
    f.Barrier(); f.raster.Drain();
    f.Expect({"begin-return:1", "end-return:1", "barrier"});
    if (!f.animator.producer_continuation_)
      throw std::runtime_error("empty frame did not preserve continuation");
    // Consume the preserved continuation so fixture teardown has no abandoned
    // pipeline item. Also prove a skipped frame does not poison the next one.
    f.Begin(2); f.End(2); f.raster.Drain();
    f.Expect({"begin-return:1", "end-return:1", "barrier", "begin-return:2",
              "end-return:2", "draw:2"});
  } else if (mode == "double-end-frame") {
    f.Begin(1, true, true); f.End(1); f.Barrier(); f.raster.Drain();
    f.Expect({"begin-return:1", "end-return:1", "draw:1", "barrier"});
  } else if (mode == "pipeline-full") {
    f.Begin(1); f.End(1); f.Begin(2); f.End(2);
    f.Begin(3); f.End(3);
    if (f.animator.retry_requests != 1 || f.shell.framework_callbacks != 2)
      throw std::runtime_error("full pipeline did not defer framework callback");
    if (!f.animator.layer_trees_tasks_.empty() ||
        f.animator.frame_timings_recorder_ || f.raster.ready.size() != 1)
      throw std::runtime_error("full pipeline changed frame commit state");
    f.raster.Drain();
    f.Expect({"begin-return:1", "end-return:1", "begin-return:2", "end-return:2",
              "begin-return:3", "end-return:3", "draw:1", "draw:2"});
  } else if (mode == "resubmission-barrier") {
    f.rasterizer.resubmissions_remaining = 1;
    f.Begin(1); f.End(1); f.Barrier(); f.raster.Drain();
    f.Expect({"begin-return:1", "end-return:1", "draw:1", "barrier", "draw:1"});
    if (f.rasterizer.resubmissions_remaining != 0)
      throw std::runtime_error("resubmission decision was not exercised");
  } else {
    return 2;
  }
  std::cout << "PASS " << mode << '\n';
}
