# Quickstart: Language Dependency Caches

## Verify an unchanged consumer call

1. Use a test consumer with `project-ci` and at least one supported manifest. Do not add cache inputs.
2. Run its CI once. Confirm a cold/miss cache does not alter the selected stages or check name.
3. Run the same commit again. Confirm the detected ecosystem reports a cache hit.
4. Add a nested `frontend/package-lock.json` fixture and confirm npm is detected while `node_modules`
   is not a cache path.

## Verify an override

1. Set one path input, such as `npm-cache-path`, in the consumer's `with:` block.
2. Confirm both npm and its cache action use that location and the other cache paths keep their defaults.
3. Leave the override empty and confirm the tool-native default is selected.

## Verify key boundaries

Check that changing a dependency lockfile changes the exact key, while restore prefixes remain within
the same runner OS, architecture, and toolchain identity. Repeat with a changed toolchain declaration
and a different runner platform.

## Verify a cache service failure

Cause a cache restore/save failure in a test consumer and confirm the selected component stages still
run and determine the existing `project-ci` verdict.
