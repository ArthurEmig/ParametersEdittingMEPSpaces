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




__output.center()

# __logger.info("All available Collectors:")
# for collector_name in available_collectors:
#     collector = qa_engine.get_collector(collector_name)
#     __output.print_md("* {} - {}".format(collector.name,collector.author))

# __logger.info("All available Analyzers:")
# for analyzer_name in available_analyzers:
#     analyzer = qa_engine.get_analyzer(analyzer_name)
#     __output.print_md("* {} by {}".format(analyzer.name,analyzer.author))



# Selector UI
class OperationSelector(forms.WPFWindow):

    def __init__(self, collectors=[], analyzers=[]):
        forms.WPFWindow.__init__(self, "SelectOperation.xaml")
        self.combo_collector.ItemsSource = collectors
        self.combo_analyzer.ItemsSource = analyzers
        self.result = False

    def btn_ok_clicked(self, sender, args):
        self.Close()
        self.result = True







__output.show()
