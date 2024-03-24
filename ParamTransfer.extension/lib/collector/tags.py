from qa_engine import Collector, get_collector
from pyrevit import HOST_APP, EXEC_PARAMS
from pyrevit import revit, DB, UI
from pyrevit import script

NAME = 'Collect tags'
DESCRIPTION = 'Collect all tags in views'
RETURN = 'list[Element]'

ARG_TYPES = {
    "Ignore Flow Arrows": bool,
    "Include Spatial Element Tags": bool,
}
# Default values of arguments
DEFAULT_ARGS = {
    "Ignore Flow Arrows": True,
    "Include Spatial Element Tags": True,
}

doc = revit.doc
uidoc = HOST_APP.uidoc
logger = script.get_logger()


def is_flow_arrow(tag):
    type_id = tag.GetTypeId()
    if type_id is None:
        return False
    type = doc.GetElement(type_id)

    return "Flow Arrow" in type.FamilyName or "FlowArrow" in type.FamilyName


def tag_filter(tag, view_ids, filter_arrows=True):
    filtered = True
    in_views = tag.OwnerViewId in view_ids
    filtered = filtered and in_views
    if filter_arrows:
        is_arrow_symbol = is_flow_arrow(tag)
        filtered = filtered and not is_arrow_symbol
    return filtered


class TagCollector(Collector):
    name = NAME
    _author = 'Junfeng Xiao'

    def collect(self, scope=[], **kwargs):

        views = scope
        filter_arrows = kwargs.get("Ignore Flow Arrows", True)
        # Independent Tags
        all_tags = list(
            DB.FilteredElementCollector(doc).OfClass(
                DB.IndependentTag).ToElements())
        # Room Tags
        if kwargs.get("Include Spatial Element Tags", True):
            room_tags = list(
                DB.FilteredElementCollector(doc).OfClass(
                    DB.SpatialElementTag).ToElements())
            all_tags += room_tags

        view_ids = map(lambda view: view.Id, views)
        tags = filter(lambda tag: tag_filter(tag, view_ids, filter_arrows),
                      all_tags)
        return tags


export = TagCollector()
