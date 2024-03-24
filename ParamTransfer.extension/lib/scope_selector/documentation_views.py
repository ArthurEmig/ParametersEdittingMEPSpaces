from qa_engine import ScopeSelector
from pyrevit import HOST_APP, EXEC_PARAMS
from pyrevit import revit, DB, UI
from pyrevit import script
from qa_report import ReportSection

# Constants

NAME = 'Documentation Views'
DESCRIPTION = 'Collect all documentation views'
AUTHOR = 'Junfeng Xiao'
RETURN = 'list[Element]'
PARAM_VIEW_GROUP = 'BHE_View Group'
PARAM_VIEW_SUBGROUP = 'BHE_View SubGroup'
ARG_TYPES = {}
DEFAULT_ARGS = {}


doc = revit.doc
uidoc = HOST_APP.uidoc
logger = script.get_logger()

def get_param_value(element, param_name):
    """Get the value of a parameter from an element"""
    param = element.LookupParameter(param_name)
    if param:
        return param.AsString()
    else:
        return None

def is_documentation_view(view):
    """Check if a view is a documentation view"""
    view_group = get_param_value(view, PARAM_VIEW_GROUP)
    in_view_group = (view_group is not None) and (view_group.find('Documentation View') != -1)
    is_not_template = not view.IsTemplate
    return in_view_group and is_not_template


class DocViewsSelector(ScopeSelector):
    name = NAME
    _author = 'Junfeng Xiao'


    def select(self, **kwargs):
        """Collect all documentation views"""
        views = DB.FilteredElementCollector(doc).OfClass(DB.View).ToElements()
        doc_views = filter(is_documentation_view, views)
        return doc_views


export = DocViewsSelector()
