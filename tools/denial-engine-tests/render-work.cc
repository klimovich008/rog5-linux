// Adapter-only fixture. Markers are replaced with exact pinned engine source.
// Native authorization/time and GPU presentation remain explicit adapters.
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
template <class T> struct WeakPtr {
  T* pointer = nullptr;
  std::weak_ptr<int> lifetime;
  explicit operator bool() const { return pointer && !lifetime.expired(); }
  T* operator->() const { assert(static_cast<bool>(*this)); return pointer; }
};
template <class T> struct WeakFactory {
  T* pointer;
  std::shared_ptr<int> lifetime = std::make_shared<int>(0);
  WeakPtr<T> GetWeakPtr() const { return {pointer, lifetime}; }
  void Invalidate() { lifetime.reset(); }
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
// Value-only graphics adapters. Production output equality/target tests execute.
struct GraphicsValue { int value = 0; bool operator==(const GraphicsValue&) const = default; };
using DlRect = GraphicsValue;
using DlISize = GraphicsValue;
using DlMatrix = GraphicsValue;
constexpr int64_t kFlutterImplicitViewId = 0;
// @OUTPUT@

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
  void AsyncWaitForVsync(Callback callback) {
    ++wait_requests;
    callback_ = std::move(callback);
  }
  unsigned wait_requests = 0;
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
  std::function<void()> pending_scene = [] {};
  unsigned notifications = 0;
  void OnDenialPendingScene() { ++notifications; pending_scene(); }
};
struct Rasterizer {
  struct DoDrawResult {
    DoDrawStatus status = DoDrawStatus::kDone;
    std::unique_ptr<FrameItem> resubmitted_item;
  };
  Rasterizer(TaskRunners runners, std::vector<std::string>& events)
      : delegate_{runners}, events_(events), weak_factory_{this} {}
  auto GetWeakPtr() { return weak_factory_.GetWeakPtr(); }
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
  const DenialRenderOutput* FindDenialRenderOutput(int64_t view) const;
  void SetDenialRenderOutputs(std::vector<DenialRenderOutput>);
  // Production CollectView also drops GPU caches, outside this fixture.
  void CollectView(int64_t view) { view_records_.erase(view); }
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
  std::vector<DenialRenderOutput> denial_render_outputs_{{-1, 1, {}, {}, 120, {}}};
  bool is_torn_down_ = false;
  std::unordered_map<int64_t, uint64_t> denial_notified_pending_scenes_;
  std::unordered_set<int64_t> denial_selected_render_view_ids_;
  bool denial_render_selection_pending_ = false;
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
// @SET_OUTPUTS@
// @FIND_OUTPUT@
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


struct Animator;
struct Engine {
  explicit Engine(Animator* animator) : animator_(animator), weak_factory_{this} {}
  void ScheduleFrame(bool);
  Animator* animator_;
  fml::WeakFactory<Engine> weak_factory_;
};

struct Shell {
  Shell(TaskRunners runners, Rasterizer* rasterizer)
      : task_runners_(runners), rasterizer_(rasterizer) {}
  void OnAnimatorDraw(std::shared_ptr<FramePipeline> pipeline);
  void OnDenialPendingScene();
  fml::WeakPtr<Engine> weak_engine_;
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
// @SHELL_PENDING@

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
  bool CanReuseLastLayerTrees();
  std::shared_ptr<DenialRenderWork> denial_render_work_;
  uint64_t denial_scene_sequence_ = 0;
  void RequestFrame(bool regenerate_layer_trees = true);
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
  bool regenerate_layer_trees_ = false;
  bool has_rendered_ = false;
  fml::Semaphore pending_frame_semaphore_{1};
  fml::TimeDelta dart_frame_deadline_;
};
// @BEGIN_FRAME@
// @END_FRAME@
// @RENDER@
// @ALL_VIEWS@
// @AWAIT_VSYNC@
// @DRAW_LAST@
// @REQUEST_FRAME@
// @CAN_REUSE@
// @ENGINE_SCHEDULE@
}  // namespace flutter

struct Fixture {
  TaskRunner ui, raster;
  TaskRunners runners{&ui, &raster};
  std::vector<std::string> events;
  flutter::Rasterizer rasterizer{runners, events};
  flutter::Shell shell{runners, &rasterizer};
  flutter::Animator animator{shell, runners};
  flutter::Engine engine{&animator};
  Fixture() {
    shell.weak_engine_ = engine.weak_factory_.GetWeakPtr();
    rasterizer.delegate_.pending_scene = [this] { shell.OnDenialPendingScene(); };
  }
  static std::unique_ptr<flutter::LayerTreeTask> Scene(uint64_t sequence,
      uint64_t generation = 1, int64_t view = -1) {
    auto task = std::make_unique<flutter::LayerTreeTask>(view,
        std::make_unique<flutter::LayerTree>(), 1);
    task->denial_scene_sequence = sequence;
    task->render_output_configuration_generation = generation;
    return task;
  }
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
             bool early_end = false, bool reuse = false) {
    shell.framework_callback = [this, render, early_end] {
      if (render) animator.Render(-1, std::make_unique<flutter::LayerTree>(), 1.0f);
      if (early_end) animator.OnAllViewsRendered();
    };
    // Legacy ownership cases inject separately granted batons, including two
    // already queued callbacks. New progress cases also exercise RequestFrame.
    animator.regenerate_layer_trees_ = !reuse;
    animator.pending_frame_semaphore_.TryWait();
    animator.AwaitVSync();
    animator.waiter_->FireCallback({}, {}, true, [this, reuse, work = std::move(work)] {
      animator.regenerate_layer_trees_ = !reuse;
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
    f.Require(f.animator.frame_scheduled_ && f.animator.waiter_->wait_requests == 4 && f.shell.framework_callbacks == 2 && f.Count("done:3") == 1, "pipeline-full work did not close");
    f.raster.Drain();
  } else if (mode == "retained-retry" || mode == "retained-reuse") {
    f.Frame(nullptr); f.ui.Drain(); f.raster.Drain();
    auto work = f.Work(1);
    if (mode == "retained-retry") {
      f.rasterizer.resubmissions_remaining = 1;
      f.shell.OnAnimatorDrawDenialRenderWork(
          std::make_unique<flutter::FrameTimingsRecorder>(), std::move(work));
    } else {
      f.Frame(std::move(work), true, false, true); f.ui.Drain();
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
  } else if (mode == "queued-ui-stale-scene-progress") {
    f.Frame(f.Work(1)); f.ui.Drain(); f.raster.Drain();
    const auto old_scene = f.rasterizer.view_records_.at(-1)
                               .last_successful_task->denial_scene_sequence;
    const auto seed_allocations = f.rasterizer.allocations;
    f.Frame(f.Work(2));  // W1: actual primary callback remains queued on UI.
    f.Require(!f.ui.ready.empty() && f.raster.ready.empty(), "W1 not UI queued");
    // Native expiry/regrant is explicit: W2 goes directly to the raster queue.
    f.shell.OnAnimatorDrawDenialRenderWork(
        std::make_unique<flutter::FrameTimingsRecorder>(), f.Work(3));
    f.raster.Drain();
    f.Require(f.rasterizer.allocations == seed_allocations + 1 &&
        f.rasterizer.view_records_.at(-1).last_successful_task->denial_scene_sequence == old_scene &&
        f.Count("begin:2") == 0, "retained W2 did not precede queued UI W1");
    f.ui.Drain(); f.raster.Drain();
    auto& pending = f.rasterizer.denial_pending_output_tasks_;
    f.Require(pending.count(-1) == 1 && pending.at(-1)->denial_scene_sequence > old_scene,
              "late W1 did not retain its newer scene");
    const auto new_scene = pending.at(-1)->denial_scene_sequence;
    f.Require(f.Count("begin:2") == 1 && f.Count("end:2") == 0 && f.Count("done:2") == 1 &&
        f.rasterizer.allocations == seed_allocations + 1, "expired W1 bypassed admission");
    if (f.ui.ready.empty()) {
      std::cerr << "FAIL progress obligation: newer deferred scene has no runnable engine continuation\n";
      return 1;
    }
    const auto builds = f.shell.framework_callbacks;
    const auto waits = f.animator.waiter_->wait_requests;
    f.ui.Drain();  // Actual Shell -> Engine -> RequestFrame -> AwaitVSync.
    f.Require(f.animator.waiter_->wait_requests == waits + 1 &&
        f.animator.waiter_->callback_ && !f.animator.regenerate_layer_trees_,
        "notification did not request one retained-scene vsync");
    // Supply a native grant only after the production waiter requested it.
    auto fresh = f.Work(4);
    f.animator.waiter_->FireCallback({}, {}, true, [&f, fresh = std::move(fresh)] {
      f.animator.denial_render_work_ = fresh;
    });
    f.ui.Drain(); f.raster.Drain();
    f.Require(f.shell.framework_callbacks == builds &&
        f.rasterizer.view_records_.at(-1).last_successful_task->denial_scene_sequence == new_scene &&
        pending.empty(), "fresh grant failed to draw pending N without another Dart build");
    f.Require(f.rasterizer.delegate_.notifications == 1 && f.ui.ready.empty() &&
        f.raster.ready.empty() && !f.animator.waiter_->callback_ && f.Count("done:4") == 1,
        "successful progress left a notification loop or retained work owner");
  } else if (mode == "pending-scene-suppression") {
    f.Frame(f.Work(1)); f.ui.Drain(); f.raster.Drain();
    f.rasterizer.StoreDenialPendingTask(Fixture::Scene(1));
    f.rasterizer.StoreDenialPendingTask(Fixture::Scene(0));
    f.Require(f.rasterizer.delegate_.notifications == 0, "drawn/equal scene notified");
    f.rasterizer.StoreDenialPendingTask(Fixture::Scene(2));
    f.rasterizer.StoreDenialPendingTask(Fixture::Scene(2));
    f.rasterizer.StoreDenialPendingTask(Fixture::Scene(1));
    f.Require(f.rasterizer.delegate_.notifications == 1 &&
        f.rasterizer.denial_pending_output_tasks_.at(-1)->denial_scene_sequence == 2,
        "duplicate/older pending scene notified or replaced newer content");
    f.shell.OnAnimatorDrawDenialRenderWork(
        std::make_unique<flutter::FrameTimingsRecorder>(), f.Work(2));
    auto replacement = f.Work(3);  // Make the retained attempt stale before draw.
    f.raster.Drain();
    f.Require(f.rasterizer.delegate_.notifications == 1 &&
        f.rasterizer.denial_pending_output_tasks_.at(-1)->denial_scene_sequence == 2 &&
        f.rasterizer.allocations == 1 && f.Count("end:2") == 0,
        "taking/re-storing the same stale pending scene notified again");
    replacement.reset();
  } else if (mode == "retained-old-scene-suppression") {
    f.Frame(f.Work(1)); f.ui.Drain(); f.raster.Drain();
    f.shell.OnAnimatorDrawDenialRenderWork(
        std::make_unique<flutter::FrameTimingsRecorder>(), f.Work(2));
    auto replacement = f.Work(3);
    f.raster.Drain();
    auto& pending = f.rasterizer.denial_pending_output_tasks_.at(-1);
    f.Require(pending->is_reused_layer_tree && pending->denial_scene_sequence == 1 &&
        !f.rasterizer.view_records_.at(-1).last_successful_task,
        "stale retained draw did not move the prior successful task");
    f.Require(f.rasterizer.delegate_.notifications == 0 && f.ui.ready.empty() &&
        f.rasterizer.allocations == 1 && f.Count("end:2") == 0,
        "already-drawn old scene was mistaken for a genuinely newer scene");
    replacement.reset();
  } else if (mode == "pending-scene-coalescing") {
    f.Frame(f.Work(1)); f.ui.Drain(); f.raster.Drain();
    const auto waits = f.animator.waiter_->wait_requests;
    f.rasterizer.StoreDenialPendingTask(Fixture::Scene(2));
    f.rasterizer.StoreDenialPendingTask(Fixture::Scene(3));
    f.rasterizer.StoreDenialPendingTask(Fixture::Scene(3));
    f.Require(f.rasterizer.delegate_.notifications == 2, "new-scene notification count incorrect");
    f.ui.Drain();
    f.Require(f.animator.waiter_->wait_requests == waits + 1 && f.ui.ready.empty() &&
        f.animator.waiter_->callback_ && !f.animator.regenerate_layer_trees_,
        "real RequestFrame semaphore failed to coalesce notifications");
  } else if (mode == "pending-scene-topology") {
    f.Frame(f.Work(1)); f.ui.Drain(); f.raster.Drain();
    f.rasterizer.StoreDenialPendingTask(Fixture::Scene(2));
    auto outputs = f.rasterizer.denial_render_outputs_;
    outputs.front().source_to_target_transform.value = 1;
    f.rasterizer.SetDenialRenderOutputs(outputs);
    f.rasterizer.StoreDenialPendingTask(Fixture::Scene(2));
    f.Require(f.rasterizer.delegate_.notifications == 1 &&
        f.rasterizer.denial_notified_pending_scenes_.at(-1) == 2,
        "presentation-only change reset the notification watermark");
    outputs.front().configuration_generation = 2;
    f.rasterizer.SetDenialRenderOutputs(outputs);
    f.Require(f.rasterizer.denial_pending_output_tasks_.empty() &&
        f.rasterizer.denial_notified_pending_scenes_.empty(), "topology retained old scene state");
    f.rasterizer.StoreDenialPendingTask(Fixture::Scene(3, 1));
    f.Require(f.rasterizer.denial_pending_output_tasks_.empty() &&
        f.rasterizer.delegate_.notifications == 1, "wrong-generation task notified");
    f.rasterizer.StoreDenialPendingTask(Fixture::Scene(2, 2));
    f.Require(f.rasterizer.delegate_.notifications == 2, "new topology did not reset watermark");
  } else if (mode == "pending-scene-scope") {
    f.rasterizer.strict = false;
    f.rasterizer.StoreDenialPendingTask(Fixture::Scene(1));
    f.Require(f.rasterizer.delegate_.notifications == 0, "legacy mode scheduled render work");
    f.rasterizer.strict = true;
    f.rasterizer.StoreDenialPendingTask(Fixture::Scene(2, 1, -2));
    f.Require(f.rasterizer.delegate_.notifications == 0, "unconfigured output notified");
    f.rasterizer.is_torn_down_ = true;
    f.rasterizer.StoreDenialPendingTask(Fixture::Scene(3));
    f.Require(f.rasterizer.delegate_.notifications == 0 &&
        f.rasterizer.denial_pending_output_tasks_.at(-1)->denial_scene_sequence == 1,
        "torn-down rasterizer accepted new pending content");
  } else if (mode == "pending-scene-weak-engine" || mode == "pending-scene-weak-animator") {
    f.rasterizer.StoreDenialPendingTask(Fixture::Scene(1));
    f.Require(f.ui.ready.size() == 1, "notification did not post to UI");
    if (mode == "pending-scene-weak-engine") {
      f.engine.weak_factory_.Invalidate();
    } else {
      f.ui.One();  // Actual Shell callback requests a frame and queues AwaitVSync.
      f.Require(f.ui.ready.size() == 1, "RequestFrame did not queue AwaitVSync");
      f.animator.weak_factory_.Invalidate();
    }
    f.ui.Drain();
    f.Require(f.animator.waiter_->wait_requests == 0 && f.raster.ready.empty(),
        "weak teardown executed a dead continuation");
  } else { return 2; }
  f.Print();
  std::cout << "PASS " << mode << '\n';
}
