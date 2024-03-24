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

ALL_CATEGORIES = map(lambda x: x.Name, doc.Settings.Categories)
"""
Constants
"""
# Human readable name of the collector
NAME = 'Collect selected elements'
# Short description of the collector
DESCRIPTION = 'Collect selected elements from the current model'
# Author
AUTHOR = 'Junfeng Xiao'
# Return value type of the collector
RETURN = 'list[Element]'
# The arguments that could be passed to the collector
ARG_TYPES = {'Category Filter': ALL_CATEGORIES}
# Default values of arguments
DEFAULT_ARGS = {'Category Filter': []}
# Hide deprecated collector
HIDDEN = True
"""
Collector class
"""


class SelectedElementsCollector(Collector):
    name = NAME
    _author = AUTHOR

    def collect(self, **kwargs):
        categorie_names = kwargs.get('Category Filter',
                                     DEFAULT_ARGS['Category Filter'])
        categories = map(lambda x: DB.Category.GetCategory(doc, x),
                         categorie_names)
        selection_ids = uidoc.Selection.GetElementIds()
        collected_elements = []
        for id in selection_ids:
            element = doc.GetElement(id)
            if element.Category in categories:
                collected_elements.append(element)
        return collected_elements


"""
Export the collector class
"""
export = SelectedElementsCollector()
