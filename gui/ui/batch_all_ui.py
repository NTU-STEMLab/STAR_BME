# -*- coding: utf8 -*-
#convert all *.ui to *.py

import os
path_list = list( os.walk( os.path.dirname( os.path.abspath( __file__ ) ) ) )
dir_ = path_list[0][0]
uilist = path_list[0][2]
uilist = [ i for i in uilist if i.endswith( ".ui" ) ]

for i in uilist:
    ui_file = os.path.join(dir_, i )
    cmd = "pyuic4 -o " + ui_file[ :-2 ]+"py " + ui_file
    print('execute command:', cmd)
    os.system( cmd )

#os.system("pyuic4 -o ui_DoBmeDlg.py ui_DoBmeDlg.ui")

