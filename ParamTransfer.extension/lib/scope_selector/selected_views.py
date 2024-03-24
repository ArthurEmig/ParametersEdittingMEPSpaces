import traceback
from qa_engine import ScopeSelector
from pyrevit import HOST_APP, EXEC_PARAMS
from pyrevit import revit, DB, UI
from pyrevit import script, forms
"""
Environment variables
"""
doc = revit.doc
uidoc = HOST_APP.uidoc
logger = script.get_logger()


def get_all_view_names():
    """Get all views from the current model without view templates"""
    views = DB.FilteredElementCollector(doc).OfClass(DB.View).ToElements()
    return [
        view.Name for view in views
        if not view.IsTemplate and hasattr(view, "Name")
    ]


"""
Constants
"""
# Human readable name of the collector
NAME = 'Selected Views'
# Short description of the collector
DESCRIPTION = 'Collect selected views (in advance settings).'
# Author
AUTHOR = 'Junfeng Xiao'
# Return value type of the collector
RETURN = 'list[Element]'
# The arguments that could be passed to the collector
ARG_TYPES = {
    "Selected Views": [],
}
# Default values of arguments
DEFAULT_ARGS = {
    "Selected Views": [],
}
"""
Collector class
"""


class ViewOption(forms.TemplateListItem):

    @property
    def name(self):
        return self.item.Name


class CurrentViewCollector(ScopeSelector):
    name = NAME
    _author = AUTHOR

    def select(self, **kwargs):
        view_names = kwargs.get("Selected Views", [])
        views = DB.FilteredElementCollector(doc).OfClass(DB.View).ToElements()
        views = [
            v for v in views
            if not v.IsTemplate and hasattr(v, "Name") and v.Name in view_names
        ]
        return views

    def show_additional_settings(self, arg_values, **kwargs):
        views = DB.FilteredElementCollector(doc).OfClass(DB.View).ToElements()
        views = [v for v in views if not v.IsTemplate and hasattr(v, "Name")]
        view_options = []
        for v in views:
            option = ViewOption(v)
            if v.Name in arg_values["Selected Views"]:
                option.checked = True
            view_options.append(option)
        result = forms.SelectFromList.show(
            view_options,
            multiselect=True,
            title="Select views",
        )
        if result and len(result) > 0:
            return {"Selected Views": [v.Name for v in result]}
        else:
            return None

    def get_description(self, **kwargs):
        try:
            text = super(ScopeSelector, self).get_description(**kwargs) + "\n"
            views = kwargs.get("Selected Views", None)
            if views:
                cropped = len(views) > 5
                text += "Selected views: "
                if cropped:
                    text += ", ".join(views[:5]) + "... "

                else:
                    text += ", ".join(views)
                text += "({} views)".format(len(views))
            else:
                text += "No view is selected currently!"
            return text
        except Exception as e:
            self.logger.error(e)
            self.logger.error(traceback.format_exc())
            return ""


"""
Export the collector class
"""
export = CurrentViewCollector()
