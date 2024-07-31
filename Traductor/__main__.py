from modules.properties import set_main_directory
set_main_directory(__file__)

from modules.gui import MainApp
app = MainApp()
app.mainloop()
