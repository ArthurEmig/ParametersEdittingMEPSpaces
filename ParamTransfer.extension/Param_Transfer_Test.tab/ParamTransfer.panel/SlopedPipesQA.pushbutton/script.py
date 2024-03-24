# coding: UTF-8

from types import ModuleType
from pyrevit import script, forms
import qa_engine
import filemgr
from qa_report import print_reports

__logger = script.get_logger()
__output = script.get_output()

available_collectors = qa_engine.get_available_modules(ModuleType.COLLECTOR)
available_analyzers = qa_engine.get_available_modules(ModuleType.ANALYZER)
available_scope_selectors = qa_engine.get_available_modules(
    ModuleType.SCOPE_SELECTOR)

__output.center()

__logger.info("All available Scope Selectors:")
for scope_selector_name in available_scope_selectors:
    scope_selector = qa_engine.get_scope_selector(scope_selector_name)
    __output.print_md("* {} - {}".format(scope_selector.name,
                                         scope_selector.author))

__logger.info("All available Collectors:")
for collector_name in available_collectors:
    collector = qa_engine.get_collector(collector_name)
    __output.print_md("* {} - {}".format(collector.name, collector.author))

__logger.info("All available Analyzers:")
for analyzer_name in available_analyzers:
    analyzer = qa_engine.get_analyzer(analyzer_name)
    __output.print_md("* {} by {}".format(analyzer.name, analyzer.author))


# Selector UI
class MultipleViewSelector(forms.WPFWindow):

    def __init__(self, scope_selectors=[], collectors=[], analyzers=[]):
        forms.WPFWindow.__init__(self, "SelectOperation.xaml")
        self.combo_scope_selector.ItemsSource = scope_selectors
        self.combo_collector.ItemsSource = collectors
        self.combo_analyzer.ItemsSource = analyzers
        self.result = False

    def btn_ok_clicked(self, sender, args):
        self.Close()
        self.result = True


# UI
select_form = MultipleViewSelector(available_scope_selectors,
                                   available_collectors, available_analyzers)

## get last selection
last_selection = filemgr.load_config("test_operation_last_selection.json")
select_form.combo_scope_selector.SelectedItem = last_selection.get(
    "scope_selector", available_scope_selectors[0])
select_form.combo_collector.SelectedItem = last_selection.get(
    "collector", available_collectors[0])
select_form.combo_analyzer.SelectedItem = last_selection.get(
    "analyzer", available_analyzers[0])

select_form.ShowDialog()

if not select_form.result:
    script.exit()

if select_form.combo_scope_selector.SelectedItem is None:
    forms.alert("No scope selector selected!")
    script.exit()

if select_form.combo_collector.SelectedItem is None:
    forms.alert("No collector selected!")
    script.exit()

if select_form.combo_analyzer.SelectedItem is None:
    forms.alert("No analyzer selected!")
    script.exit()

# save selection
filemgr.save_config(
    {
        "collector": select_form.combo_collector.SelectedItem,
        "analyzer": select_form.combo_analyzer.SelectedItem,
        "scope_selector": select_form.combo_scope_selector.SelectedItem,
    }, "test_operation_last_selection.json")

operation = qa_engine.Operation(
    name="Test Operation",
    scope_selector=select_form.combo_scope_selector.SelectedItem,
    collector=select_form.combo_collector.SelectedItem,
    analyzer=select_form.combo_analyzer.SelectedItem)

__logger.info("Operation initialized: {}".format(operation))

report = operation.run()

report.name = "Test: {scope} - {collector} - {analyzer}".format(
    scope=select_form.combo_scope_selector.SelectedItem,
    collector=select_form.combo_collector.SelectedItem,
    analyzer=select_form.combo_analyzer.SelectedItem)

report.print_details = True

print_reports(
    name="Test Report",
    report_sections=[report],
    description="This is an example report generated by QAEngine",
)

__output.show()
