from pyrevit import script, forms
import qa_engine
import filemgr
from qa_report import print_reports
import clr
clr.AddReference('System.Windows.Forms')
clr.AddReference('IronPython.wpf')

xamlfile = script.get_bundle_file('SelectFamilyTypesParams.xaml')

import wpf
from System import Windows

class MyWindow(Windows.Window):

    def __init__(self):
        wpf.LoadComponent(self, xamlfile)


MyWindow().ShowDialog()

