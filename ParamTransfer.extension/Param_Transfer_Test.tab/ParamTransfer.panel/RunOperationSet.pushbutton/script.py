from os import path
from pyrevit import script, forms
import qa_engine
import filemgr
from qa_report import print_reports
from qa_ui.config_manager import ConfigMgr
from qa_ui.config_manager import CONFIG_EXTENSION

__logger = script.get_logger()
__output = script.get_output()



operation_set_path = forms.pick_file(
    file_ext=CONFIG_EXTENSION[1:],
    init_dir= path.join(filemgr.get_user_config_path(),"OperationSet"),
    title="Select Operation Set to Run",
)

if not operation_set_path:
    script.exit()

operation_set = qa_engine.OperationSet.from_config_file(operation_set_path)

if not operation_set:
    forms.alert("Operation Set is not valid", exitscript=True)

report_sections = operation_set.run()


print_reports(operation_set.name, report_sections, operation_set.description)