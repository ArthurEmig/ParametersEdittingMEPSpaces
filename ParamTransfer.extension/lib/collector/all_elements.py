from qa_engine import Collector
from qa_report import ReportSection, ReportItem
from pyrevit import HOST_APP, EXEC_PARAMS
from pyrevit import revit, DB, UI
from pyrevit import script,forms
import clr

clr.AddReference("System")
from System.Collections.Generic import List

doc = revit.doc
ALL_CATEGORIES = map(lambda x: x.Name, doc.Settings.Categories)
ALL_CATEGORIES.sort()

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
NAME = 'Collect all elements'
# Short description of the collector
DESCRIPTION = 'Collect all elements from the current file under selected categories and return them in a list.'
# Author
AUTHOR = 'AUTHOR'
# Return value type of the collector
RETURN = 'list[Element]'
# The arguments that could be passed to the collector
ARG_TYPES = {'Category Filter': ALL_CATEGORIES}
# Default values of arguments
DEFAULT_ARGS = {'Category Filter': ALL_CATEGORIES}

HIDDEN = True

"""
Collector class
"""


class AllElementsCollector(Collector):
    name = NAME
    _author = AUTHOR

    def collect(self, scope=[], **kwargs):
        categories = kwargs['Category Filter']
        categories = map(
            lambda x: [c.Id for c in doc.Settings.Categories
                       if c.Name == x][0], categories)
        categories = List[DB.ElementId](categories)
        filter = DB.ElementMulticategoryFilter(categories)
        result = set()
        for view in scope:
            result.update(
                DB.FilteredElementCollector(
                    doc, view.Id).WherePasses(filter).ToElements())
        if len(scope) == 0:
            result.update(
                DB.FilteredElementCollector(doc).WherePasses(
                    filter).ToElements())
        self.total_count = len(result)
        return list(result)
    
    def show_additional_settings(self, arg_values, **kwargs):
        selected = arg_values.get("Category Filter", [])
        cat_options = []
        for cat in ALL_CATEGORIES:
            option = forms.TemplateListItem(cat)
            if cat in selected:
                option.checked = True
            cat_options.append(option)
        cat_options.sort(key=lambda x: (not x.checked, x.name))
        result = forms.SelectFromList.show(
            cat_options,
            multiselect=True,
            title="Category Filter",
        )
        if result and len(result) > 0:
            return {"Category Filter": result}
        else:
            return None

    def decorate_report_section(self, report_section):
        # type: (ReportSection) -> ReportSection
        report_section.total_count = self.total_count
        return report_section


"""
Export the collector class
"""
export = AllElementsCollector()
