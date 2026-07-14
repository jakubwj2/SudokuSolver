# Commands for running the app

## Build debug

```bash {cmd}
source .venv/bin/activate &&
buildozer android debug deploy run logcat > android_log.log
```

## Deploy the Solver

```bash {cmd}
source .venv/bin/activate &&
buildozer android deploy run logcat > android_log.log
```

## Release build

```bash {cmd}
source .venv/bin/activate &&
buildozer android release deploy run
```

## Copy images from phone

```bash {cmd}
adb pull /sdcard/DCIM/SudokuPhotos ./SudokuPhotos
```
