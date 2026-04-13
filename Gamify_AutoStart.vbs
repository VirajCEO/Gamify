Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Users\viraj\OneDrive\Desktop\Gamify"
' 0 means completely hide window, False means don't wait for execution to finish
WshShell.Run "pythonw app.py", 0, False
