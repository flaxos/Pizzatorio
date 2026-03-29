extends Node

## Time Manager handles fixed deterministic ticking.
## Replaces --ticks --dt run configurations from python main loop.

var current_tick: int = 0
var tick_accumulator: float = 0.0
var speed_multiplier: float = 1.0
var _is_paused: bool = false
var _headless: bool = false

func _ready() -> void:
    # Check if we should run at maximum speed in headless mode
    var args = OS.get_cmdline_args()
    if "--headless" in args:
        _headless = true
        Engine.time_scale = 10.0 # Run faster for simulation checks
        print("TimeManager started in HEADLESS mode.")

func _physics_process(delta: float) -> void:
    if _is_paused:
        return
        
    tick_accumulator += delta * speed_multiplier
    
    # Process ticks deterministically
    while tick_accumulator >= GlobalConfig.TICK_RATE:
        tick_accumulator -= GlobalConfig.TICK_RATE
        _tick()

func _tick() -> void:
    current_tick += 1
    EventBus.on_tick.emit(current_tick)
    
func toggle_pause() -> void:
    _is_paused = !_is_paused

func toggle_fast_forward() -> void:
    speed_multiplier = 1.0 if speed_multiplier > 1.0 else 3.0
