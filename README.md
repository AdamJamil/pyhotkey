This project is a combination of a script that adds many utilities to my keyboard, as well as a script that allows for on-the-fly scheduling in a non-obstrusive way. 

The keyboard utilities include text navigation & highlighting, inserting common symbols, adjusting the system volume and using the mouse, all without repositioning the hands away from the home row. 

Currently, there is no easy way to allow Python to consume keyboard events on Linux, meaning that this will only work on Windows for now. I ~~do not have plans to recreate this for macOS~~ have recreated this in macOS but refuse to upload the code here as it is unholy.

The scheduling utitilies provides a command line-esque interface for quickly adding things that the user will be reminded of. It is heavily under work at the moment. Currently, the user is reminded of tasks via win10toast.
