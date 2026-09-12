// Adapter-only fixture. Markers are replaced with exact pinned engine source.
// This characterizes queue ordering; it does not implement a reservation fix.
#include <algorithm>
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
#include <type_traits>
#include "source/engine/src/flutter/shell/platform/embedder/embedder.h"
#include <vector>

#define SLIMPELLER 1
#define NOT_SLIMPELLER(...)
#define TRACE_EVENT0_WITH_FLOW_IDS(...) Trace(__VA_ARGS__)
#define FML_TRACE_EVENT_WITH_FLOW_IDS(...) Trace(__VA_ARGS__)
#define TRACE_FLOW_BEGIN(...) Trace(__VA_ARGS__)
using WorkBegin = int32_t (*)(void*, int64_t, uint64_t, uint32_t, uint32_t);
using WorkEnd = void (*)(void*, int64_t, uint64_t);
using WorkDone = void (*)(void*, uint64_t);
using SetWorkCallbacks = FlutterEngineResult (*)(FlutterEngine, WorkBegin, WorkEnd, WorkDone, void*);
using RenderWithWork = FlutterEngineResult (*)(FlutterEngine, const int64_t*, size_t,
    const int64_t*, size_t, bool, uint64_t, uint64_t, uint64_t, intptr_t);
static_assert(std::is_same_v<decltype(&DenialFlutterEngineSetRenderWorkCallbacks), SetWorkCallbacks>);
static_assert(std::is_same_v<decltype(&DenialFlutterEngineRenderOutputsWithWork), RenderWithWork>);

template <typename... T> void Trace(const T&...) {}
#define TRACE_EVENT0(...) Trace(__VA_ARGS__)
#define TRACE_EVENT_INSTANT0(...) Trace(__VA_ARGS__)
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
  bool operator>=(TimePoint) const { return true; }
  bool operator>(TimePoint) const { return false; }
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
template <class T> auto MakeCopyable(T closure) {
  auto owned = std::make_shared<T>(std::move(closure));
  return [owned] { (*owned)(); };
}
using closure = std::function<void()>;
using TaskQueueId = int;
namespace tracing { uint64_t TraceNonce() { return 1; } }
class ScopedCleanupClosure {
 public:
  explicit ScopedCleanupClosure(closure callback) : callback_(std::move(callback)) {}
  ~ScopedCleanupClosure() { callback_(); }
 private:
  closure callback_;
};
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
  int GetTaskQueueId() const { return 1; }
  void One() {
    if (ready.empty()) throw std::runtime_error("empty queue");
    auto task = std::move(ready.front()); ready.pop_front(); task();
  }
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
struct LayerTree {
  struct Size { int width = 32; int height = 24; };
  Size frame_size() const { return {}; }
};
struct FrameTimingsRecorder {
  explicit FrameTimingsRecorder(uint64_t id = 0) : number(id) {}
  uint64_t number;
  enum class State { kBuildEnd, kRasterEnd };
  void AssertInState(State) const {}
  int GetBuildDuration() const { return 0; }
  void RecordRasterStart(fml::TimePoint) {}
  void RecordRasterEnd() {}
  std::unique_ptr<FrameTimingsRecorder> CloneUntil(State) const {
    return std::make_unique<FrameTimingsRecorder>(number);
  }
  void RecordBuildStart(fml::TimePoint) {}
  void RecordBuildEnd(fml::TimePoint) {}
  void RecordVsync(fml::TimePoint, fml::TimePoint) {}
  fml::TimePoint GetVsyncTargetTime() const { return {}; }
  uint64_t GetFrameNumber() const { return number; }
};
struct LayerTreeTask {
  LayerTreeTask(int64_t id, std::unique_ptr<LayerTree> tree, float ratio)
      : view_id(id), layer_tree(std::move(tree)), device_pixel_ratio(ratio) {}
  int64_t view_id;
  std::unique_ptr<LayerTree> layer_tree;
  float device_pixel_ratio;
  bool is_reused_layer_tree = false;
  std::optional<std::unordered_set<int64_t>> dirty_texture_ids;
  // Tests provide already-projected synthetic output tasks at this seam.
  std::optional<uint64_t> render_output_configuration_generation = 1;
  uint64_t denial_scene_sequence = 0;
};
// @WORK@
// @FRAME_ITEM@

enum class DrawSurfaceStatus { kSuccess, kRetry, kFailed, kDiscarded, kDeferred };
struct DenialRenderOutput {};
struct Surface { void* GetContext() const { return nullptr; } };
struct CompositorContext {
  struct Timer { void SetLapTime(int) {} };
  Timer timer;
  Timer& ui_time() { return timer; }
};
namespace denial_render_audit {
struct Scope { explicit Scope(const char*) {} };
template <typename... T> void Record(const T&...) {}
}
const char* kVsyncFlowName = "vsync";
const char* kVsyncTraceName = "vsync-process";
struct VsyncWaiter {
  using Callback = std::function<void(std::unique_ptr<FrameTimingsRecorder>)>;
  explicit VsyncWaiter(TaskRunners runners) : task_runners_(runners) {}
  void AsyncWaitForVsync(Callback callback) { callback_ = std::move(callback); }
  void FireCallback(fml::TimePoint, fml::TimePoint, bool = true, fml::closure = nullptr);
  void PauseDartEventLoopTasks() {}
  static void ResumeDartEventLoopTasks(int) {}
  std::mutex callback_mutex_;
  Callback callback_;
  std::unordered_map<uintptr_t, fml::closure> secondary_callbacks_;
  TaskRunners task_runners_;
};
// @FIRE_CALLBACK@

enum class DrawStatus { kYielded, kPipelineEmpty, kDone };
enum class DoDrawStatus { kDone, kEnqueuePipeline };
struct ThreadMerger { bool IsOnRasterizingThread() const { return true; } };
struct ExternalViewEmbedder {
  bool GetUsedThisFrame() const { return false; }
  void SetUsedThisFrame(bool) {}
  void EndFrame(bool, const std::shared_ptr<ThreadMerger>&) {}
  void BeginFrame(void*, const std::shared_ptr<ThreadMerger>&) {}
};
struct RasterDelegate {
  TaskRunners runners;
  const TaskRunners& GetTaskRunners() const { return runners; }
  bool ShouldDiscardLayerTree(int64_t, const LayerTree&) const { return false; }
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
    events_.push_back("draw:" + std::to_string(active_denial_render_work_ ? active_denial_render_work_->id : 0));
    if (active_denial_render_work_) {
      const auto& ids = active_denial_render_work_->texture_identifiers;
      const std::unordered_set<int64_t> expected(ids.begin(), ids.end());
      for (const auto& task : tasks) {
        if (!task->dirty_texture_ids || *task->dirty_texture_ids != expected)
          throw std::runtime_error("texture selection leaked across work");
      }
    }
    return {.status = DoDrawStatus::kDone,
            .resubmitted_item = DrawToSurfacesUnsafe(*recorder, std::move(tasks))};
  }
  // Projection/GPU boundary adapter: tasks already carry synthetic view IDs.
  std::vector<std::unique_ptr<LayerTreeTask>> ExpandDenialRenderOutputTasks(
      std::vector<std::unique_ptr<LayerTreeTask>> tasks) { return tasks; }
  std::unique_ptr<FrameItem> DrawToSurfacesUnsafe(FrameTimingsRecorder&,
      std::vector<std::unique_ptr<LayerTreeTask>>);
  DrawSurfaceStatus DrawToSurfaceUnsafe(int64_t, LayerTree&, const LayerTree*,
      const std::unordered_set<int64_t>*, float, std::optional<fml::TimePoint>);
  void StoreDenialPendingTask(std::unique_ptr<LayerTreeTask>);
  void ResubmitDenialRenderWork(std::unique_ptr<FrameItem>);
  void MarkDenialWorkTextures() {}
  void MarkTextureFrameAvailable(int64_t) {}
  std::unique_ptr<LayerTreeTask> ReprojectDenialRenderOutputTask(
      const DenialRenderOutput&, const LayerTreeTask&) { return nullptr; }
  DoDrawResult DrawToSurfaces(FrameTimingsRecorder& recorder,
                            std::vector<std::unique_ptr<LayerTreeTask>> tasks) {
    return {.status = DoDrawStatus::kDone,
            .resubmitted_item = DrawToSurfacesUnsafe(recorder, std::move(tasks))};
  }
  void DrawDenialRenderOutputs(std::vector<int64_t>, std::vector<int64_t>,
      std::unique_ptr<FrameTimingsRecorder>, std::shared_ptr<DenialRenderWork> = nullptr);
  bool UsesDenialRenderWork() const { return strict; }
  const DenialRenderOutput* FindDenialRenderOutput(int64_t view) const {
    static DenialRenderOutput output;
    return view < 0 ? &output : nullptr;
  }
  struct ViewRecord {
    DrawSurfaceStatus last_draw_status = DrawSurfaceStatus::kDiscarded;
    std::unique_ptr<LayerTreeTask> last_successful_task;
  };
  ViewRecord& EnsureViewRecord(int64_t view) { return view_records_[view]; }
  const LayerTree* GetLastLayerTree(int64_t view) {
    auto& task = view_records_[view].last_successful_task;
    return task ? task->layer_tree.get() : nullptr;
  }
  void FireNextFrameCallbackIfPresent() {}
  unsigned resubmissions_remaining = 0;
  unsigned allocations = 0;
  bool fail_allocation = false;
  bool strict = true;
  uint64_t denial_render_output_generation_ = 1;
  std::shared_ptr<DenialRenderWork> active_denial_render_work_;
  std::unordered_map<int64_t, ViewRecord> view_records_;
  std::unordered_map<int64_t, std::unique_ptr<LayerTreeTask>> denial_pending_output_tasks_;
  std::unique_ptr<Surface> surface_ = std::make_unique<Surface>();
  std::unique_ptr<CompositorContext> compositor_context_ = std::make_unique<CompositorContext>();
  RasterDelegate delegate_;
  std::vector<std::string>& events_;
  fml::WeakFactory<Rasterizer> weak_factory_;
  std::shared_ptr<ThreadMerger> raster_thread_merger_;
  std::unique_ptr<ExternalViewEmbedder> external_view_embedder_;
  std::unordered_set<int64_t> pending_texture_ids_;
};
// @DRAW@
// @RESUBMIT@
// @STORE_PENDING@
// @RESUBMIT_WORK@
// @DRAW_RETAINED@
// @DRAW_SURFACES@
// @DRAW_SURFACE_PREFIX@
  // Adapted GPU boundary: production admission above must have completed first.
  Trace(previous_layer_tree, dirty_texture_ids, device_pixel_ratio, presentation_time);
  ++allocations;
  if (fail_allocation) return DrawSurfaceStatus::kFailed;
  if (resubmissions_remaining > 0) {
    --resubmissions_remaining;
    return DrawSurfaceStatus::kRetry;
  }
  return DrawSurfaceStatus::kSuccess;
}


struct Shell {
  Shell(TaskRunners runners, Rasterizer* rasterizer)
      : task_runners_(runners), rasterizer_(rasterizer) {}
  void OnAnimatorDraw(std::shared_ptr<FramePipeline> pipeline);
  void OnAnimatorDrawLastLayerTrees(std::unique_ptr<FrameTimingsRecorder>) {
    throw std::runtime_error("legacy reuse outside fixture scope");
  }
  void OnAnimatorDrawDenialRenderWork(std::unique_ptr<FrameTimingsRecorder>,
                                    std::shared_ptr<DenialRenderWork>);
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
// @SHELL_DRAW_WORK@

struct Animator {
  Animator(Shell& shell, TaskRunners runners)
      : delegate_(shell), task_runners_(runners), weak_factory_{this},
        waiter_(std::make_unique<VsyncWaiter>(runners)) {}
  void BeginFrame(std::unique_ptr<FrameTimingsRecorder> recorder);
  void EndFrame();
  void Render(int64_t, std::unique_ptr<LayerTree>, float);
  void OnAllViewsRendered();
  void AwaitVSync();
  void DrawLastLayerTrees(std::unique_ptr<FrameTimingsRecorder>);
  bool reuse_last = false;
  bool CanReuseLastLayerTrees() const { return reuse_last; }
  std::shared_ptr<DenialRenderWork> denial_render_work_;
  uint64_t denial_scene_sequence_ = 0;
  // Observe the source's retry decision without adapting another vsync cycle.
  void RequestFrame() { ++retry_requests; }
  unsigned retry_requests = 0;
  Shell& delegate_;
  TaskRunners task_runners_;
  fml::WeakFactory<Animator> weak_factory_;
  std::unique_ptr<VsyncWaiter> waiter_;
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
// @AWAIT_VSYNC@
// @DRAW_LAST@
}  // namespace flutter

struct Fixture {
  TaskRunner ui, raster;
  TaskRunners runners{&ui, &raster};
  std::vector<std::string> events;
  flutter::Rasterizer rasterizer{runners, events};
  flutter::Shell shell{runners, &rasterizer};
  flutter::Animator animator{shell, runners};
  uint64_t newest_work = 0;
  int32_t admission_override = 1;
  static int32_t Begin(void* data, int64_t view, uint64_t work, uint32_t width, uint32_t height) {
    auto& f = *static_cast<Fixture*>(data);
    if (view != -1 || width != 32 || height != 24) throw std::runtime_error("bad admission target");
    f.events.push_back("begin:" + std::to_string(work));
    return work == f.newest_work ? f.admission_override : 0;
  }
  static void End(void* data, int64_t, uint64_t work) {
    static_cast<Fixture*>(data)->events.push_back("end:" + std::to_string(work));
  }
  static void Done(void* data, uint64_t work) {
    static_cast<Fixture*>(data)->events.push_back("done:" + std::to_string(work));
  }
  std::shared_ptr<flutter::DenialRenderWork> Work(uint64_t id) {
    newest_work = id;
    return std::make_shared<flutter::DenialRenderWork>(id, std::vector<int64_t>{-1},
        std::vector<int64_t>{static_cast<int64_t>(id)},
        flutter::DenialRenderWork::Callbacks{Begin, End, Done, this});
  }
  void Frame(std::shared_ptr<flutter::DenialRenderWork> work, bool render = true,
             bool early_end = false) {
    shell.framework_callback = [this, render, early_end] {
      if (render) animator.Render(-1, std::make_unique<flutter::LayerTree>(), 1.0f);
      if (early_end) animator.OnAllViewsRendered();
    };
    animator.AwaitVSync();
    animator.waiter_->FireCallback({}, {}, true, [this, work = std::move(work)] {
      animator.denial_render_work_ = work;
    });
  }
  void Require(bool value, const char* message) {
    if (!value) throw std::runtime_error(message);
  }
  size_t Count(const std::string& event) const { return std::count(events.begin(), events.end(), event); }
  void Print() { for (const auto& event : events) std::cout << event << '\n'; }
};

int main(int argc, char** argv) {
  if (argc != 2) return 2;
  const std::string mode = argv[1];
  Fixture f;
  if (mode == "zero-item") {
    f.Frame(f.Work(1), false);
    f.Require(f.Count("done:1") == 0, "work closed before primary callback");
    f.ui.Drain();
    f.Require(f.Count("done:1") == 1 && f.raster.ready.empty(), "empty frame did not close once");
    f.Require(!f.animator.denial_render_work_, "empty frame leaked work");
  } else if (mode == "interleaved") {
    f.Frame(f.Work(1)); f.Frame(f.Work(2)); f.ui.Drain();
    f.Require(f.Count("done:1") == 0 && f.Count("done:2") == 0, "queued ownership released early");
    f.raster.Drain();
    f.Require(f.Count("begin:1") == 1 && f.Count("begin:2") == 1, "primary callbacks misassociated work");
    f.Require(f.Count("end:1") == 0 && f.Count("end:2") == 1, "stale work admitted");
    f.Require(f.rasterizer.allocations == 1 && f.Count("done:1") == 1 && f.Count("done:2") == 1, "bad draw ownership");
  } else if (mode == "stale-pending") {
    f.Frame(f.Work(1)); f.ui.Drain(); auto newer = f.Work(2); f.raster.Drain();
    f.Require(f.rasterizer.allocations == 0 && f.Count("done:1") == 1, "stale work allocated");
    auto& pending = f.rasterizer.denial_pending_output_tasks_;
    f.Require(pending.at(-1)->denial_scene_sequence == 1, "stale scene not retained");
    auto old = std::make_unique<flutter::LayerTreeTask>(-1, std::make_unique<flutter::LayerTree>(), 1);
    old->denial_scene_sequence = 0;
    f.rasterizer.StoreDenialPendingTask(std::move(old));
    f.Require(pending.at(-1)->denial_scene_sequence == 1, "old scene replaced newer pending scene");
    newer.reset();
  } else if (mode == "stale-topology") {
    f.Frame(f.Work(1)); f.ui.Drain();
    f.rasterizer.denial_render_output_generation_ = 2;
    f.raster.Drain();
    f.Require(f.rasterizer.allocations == 0 && f.Count("begin:1") == 0 && f.Count("done:1") == 1, "old topology reached allocation");
    f.Require(f.rasterizer.denial_pending_output_tasks_.empty(), "old topology was retained");
  } else if (mode == "untagged") {
    f.Frame(nullptr); f.ui.Drain(); f.raster.Drain();
    f.Require(f.rasterizer.allocations == 0 && f.rasterizer.denial_pending_output_tasks_.count(-1) == 1, "untagged frame was not retained");
  } else if (mode == "resubmission") {
    f.rasterizer.resubmissions_remaining = 1;
    f.Frame(f.Work(1)); f.ui.Drain(); f.raster.One();
    f.Require(f.Count("done:1") == 0, "retry released work before repost");
    f.raster.Drain();
    f.Require(f.Count("begin:1") == 2 && f.Count("end:1") == 2 && f.Count("done:1") == 1, "retry did not retain exact work");
    f.Require(!f.rasterizer.active_denial_render_work_, "raster scope leaked");
  } else if (mode == "early-end") {
    f.Frame(f.Work(1), true, true); f.ui.Drain(); f.raster.Drain();
    f.Require(f.Count("draw:1") == 1 && f.Count("done:1") == 1, "early/outer end double completed");
  } else if (mode == "pipeline-full") {
    f.Frame(f.Work(1)); f.ui.Drain(); f.Frame(f.Work(2)); f.ui.Drain();
    f.Frame(f.Work(3)); f.ui.Drain();
    f.Require(f.animator.retry_requests == 1 && f.shell.framework_callbacks == 2 && f.Count("done:3") == 1, "pipeline-full work did not close");
    f.raster.Drain();
  } else if (mode == "retained-retry" || mode == "retained-reuse") {
    f.Frame(nullptr); f.ui.Drain(); f.raster.Drain();
    auto work = f.Work(1);
    if (mode == "retained-retry") {
      f.rasterizer.resubmissions_remaining = 1;
      f.shell.OnAnimatorDrawDenialRenderWork(
          std::make_unique<flutter::FrameTimingsRecorder>(), std::move(work));
    } else {
      f.animator.reuse_last = true;
      f.Frame(std::move(work)); f.ui.Drain();
      f.Require(f.shell.framework_callbacks == 1, "retained reuse unexpectedly called Dart");
    }
    f.raster.One();
    if (mode == "retained-retry") f.Require(f.Count("done:1") == 0, "retained retry closed before its pipeline");
    f.raster.Drain();
    f.Require(f.Count("done:1") == 1 && f.rasterizer.denial_pending_output_tasks_.empty(), "retained work did not close");
    f.Require(f.rasterizer.view_records_.at(-1).last_successful_task != nullptr, "retained scene was lost");
  } else if (mode == "real-error") {
    f.admission_override = -1;
    f.Frame(f.Work(1)); f.ui.Drain(); f.raster.Drain();
    f.Require(f.rasterizer.allocations == 0 && f.Count("end:1") == 0 && f.Count("done:1") == 1, "real admission error cleanup incorrect");
    f.Require(f.rasterizer.view_records_.at(-1).last_draw_status == flutter::DrawSurfaceStatus::kFailed && f.rasterizer.denial_pending_output_tasks_.empty(), "real error was swallowed as stale");
  } else if (mode == "allocation-failure") {
    f.rasterizer.fail_allocation = true;
    f.Frame(f.Work(1)); f.ui.Drain(); f.raster.Drain();
    f.Require(f.Count("end:1") == 1 && f.Count("done:1") == 1 && f.rasterizer.denial_pending_output_tasks_.empty(), "failure did not release admitted scope");
  } else { return 2; }
  f.Print();
  std::cout << "PASS " << mode << '\n';
}
