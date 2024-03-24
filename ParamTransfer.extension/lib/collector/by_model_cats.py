from qa_engine import Collector
from qa_report import ReportSection, ReportItem
from pyrevit import HOST_APP, EXEC_PARAMS
from pyrevit import revit, DB, UI
from pyrevit import script, forms
import clr

clr.AddReference("System")
from System.Collections.Generic import List

doc = revit.doc
ALL_CATEGORIES = [c for c in doc.Settings.Categories if c.CategoryType == DB.CategoryType.Model]
ALL_CATEGORIES = map(lambda x: x.Name, ALL_CATEGORIES)
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
NAME = 'By Model Categories'
# Short description of the collector
DESCRIPTION = 'Select elements by Model Categories'
# Author
AUTHOR = 'Junfeng Xiao'
# Return value type of the collector
RETURN = 'list[Element]'
# The arguments that could be passed to the collector
ARG_TYPES = {'Category Filter': ALL_CATEGORIES}
# Default values of arguments
DEFAULT_ARGS = {'Category Filter': []}


"""
Collector class
"""


class CategoryElementsCollector(Collector):
    name = NAME
    _author = AUTHOR
    MAX_CAT_IN_DESC = 5

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

    def get_description(self, **kwargs):
        desc = DESCRIPTION
        cat_names = kwargs.get('Category Filter', [])
        if len(cat_names) == 0:
            desc += "\nNo category is selected!"
        else:
            desc += "\nSelected categories: "
            if len(cat_names) > self.MAX_CAT_IN_DESC:
                desc += ", ".join(cat_names[:self.MAX_CAT_IN_DESC]) + " and " + str(len(cat_names) - self.MAX_CAT_IN_DESC) + " more"
            else:
                desc += ", ".join(cat_names)
        return desc
    
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
export = CategoryElementsCollector()
