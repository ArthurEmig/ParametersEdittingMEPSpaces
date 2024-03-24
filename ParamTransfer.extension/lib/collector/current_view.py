from qa_engine import Collector
from pyrevit import HOST_APP, EXEC_PARAMS
from pyrevit import revit, DB, UI
from pyrevit import script
"""
Environment variables
"""
doc = revit.doc
uidoc = HOST_APP.uidoc
logger = script.get_logger()
"""
Constants
"""
# Human readable name of the collector
NAME = 'Collect active view'
# Short description of the collector
DESCRIPTION = 'Collect active view from the current model and return as a list.'
# Author
AUTHOR = 'Junfeng Xiao'
# Return value type of the collector
RETURN = 'list[Element]'
# The arguments that could be passed to the collector
ARG_TYPES = {}
# Default values of arguments
DEFAULT_ARGS = {}

# Hide deprecated collector
HIDDEN = True
"""
Collector class
"""


class CurrentViewCollector(Collector):
    name = NAME
    _author = AUTHOR

    def collect(self, **kwargs):
        return [doc.ActiveView]


"""
Export the collector class
"""
export = CurrentViewCollector()
