---
name: fix-headless-tests
description: Fix the headless test runner SceneTree init bug and restore the quality gate
---

# Fix Headless Test Runner

## Problem

`test_headless.gd` crashes at line 29 with:
```
ERROR: Parameter "data.tree" is null.
SCRIPT ERROR: Invalid access to property or key 'process_frame' on a base object of type 'null instance'.
```

The script `extends SceneTree`, so inside `_init()`, `root.get_tree()` returns null because the tree isn't fully initialized yet during `_init()`.

## Fix Strategy

The issue is that `await root.get_tree().process_frame` is called in `_init()` but the SceneTree isn't ready yet. Since the script IS the SceneTree, use `await process_frame` directly (self is the tree), or move the test logic to `_initialize()` which is called after the tree is set up.

**Preferred approach:** Override `_initialize()` instead of `_init()`, which runs after the SceneTree is fully constructed. Or use `await self.process_frame` since `self` is the SceneTree.

## Steps

1. Read `test_headless.gd` at `/home/flax/games/pizzatorio/v2_godot/test_headless.gd`
2. Fix the null SceneTree access — change `await root.get_tree().process_frame` to `await process_frame` (since the script extends SceneTree, `self` has the signal)
3. Verify the fix works: run `~/bin/godot --headless --script res://test_headless.gd` from the project directory
4. If the test passes (prints "ALL TESTS PASSED" and exits 0), the fix is complete
5. If there are further failures, debug and fix them

## Validation

```bash
cd /home/flax/games/pizzatorio/v2_godot
timeout 15 ~/bin/godot --headless --script res://test_headless.gd 2>&1
# Expected: "--- ALL TESTS PASSED ---" and exit code 0
```

## Files

- `/home/flax/games/pizzatorio/v2_godot/test_headless.gd` — the test runner to fix
- `/home/flax/games/pizzatorio/v2_godot/src/game/SimulationCore.gd` — the system under test
- `/home/flax/games/pizzatorio/v2_godot/src/autoloads/GlobalConfig.gd` — dependency
