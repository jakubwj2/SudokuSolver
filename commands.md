# copy images from phone
adb pull /sdcard/DCIM/SudokuPhotos ./SudokuPhotos

# deploy the solver
buildozer android deploy run logcat > android_log.log