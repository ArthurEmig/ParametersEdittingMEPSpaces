import trace
import traceback
from pyrevit import script, forms
import qa_engine
import filemgr
from qa_report import print_reports
from qa_ui.config_manager import ConfigMgr


__logger = script.get_logger()
__output = script.get_output()

__output.center()

try:
    config_manager = ConfigMgr()

    config_manager.Show()
except Exception as ex:
    __logger.error(ex)
    __logger.error(traceback.format_exc())
    forms.alert("Failed to open QA Manager. See log for details.", title="QA Manager")
    