extends RefCounted
# Preview-only detector for a rapid half turn.
var window_seconds := 0.5
var threshold_180 := deg_to_rad(180.0)
var elapsed := 0.0
var previous_yaw := 0.0
var initialized := false
var samples: Array[Vector2] = []

func sample_yaw(yaw: float, delta: float, moving := false, busy := false) -> int:
 elapsed += delta
 if not initialized or moving or busy:
  previous_yaw = yaw
  initialized = true
  samples.clear()
  return 0
 var change := angle_difference(previous_yaw, yaw)
 previous_yaw = yaw
 if absf(change) > 0.0001:
  samples.append(Vector2(elapsed, change))
 while not samples.is_empty() and elapsed - samples[0].x > window_seconds:
  samples.pop_front()
 var total := 0.0
 for entry in samples:
  total += entry.y
 var degrees := 0
 if absf(total) + 0.0001 >= threshold_180:
  degrees = 180
 if degrees != 0:
  samples.clear()
  return degrees if total > 0 else -degrees
 return 0
