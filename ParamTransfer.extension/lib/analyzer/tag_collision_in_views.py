from qa_engine import Analyzer
from qa_report import ReportSection, ReportItem, ReportGroupType
from pyrevit import HOST_APP, EXEC_PARAMS
from pyrevit import revit, DB, UI
from pyrevit import script
import qa_engine
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
NAME = 'Tag Collision In Views Analyzer'
# Short description of the collector
DESCRIPTION = """
This analyzer receives a list of views and checks if there are any tag collisions in these views.
"""
# Author
AUTHOR = 'Junfeng Xiao'
# The arguments that could be passed to the analyzer
ARG_TYPES = {
    "Ignore Flow Direction Arrows": bool,
    "Include Spatial Element Tags": bool,
    "Sensitivity": float,
}
# Default values of arguments
DEFAULT_ARGS = {
    "Ignore Flow Direction Arrows": True,
    "Include Spatial Element Tags": True,
    "Sensitivity": 0.6,
}

# Hide deprecated collector
HIDDEN = True
"""
Environment variables

"""
doc = revit.doc
uidoc = HOST_APP.uidoc
logger = script.get_logger()


def is_flow_arrow(tag):
    type_id = tag.GetTypeId()
    if type_id is None:
        return False
    type = doc.GetElement(type_id)

    return "Flow Arrow" in type.FamilyName or "FlowArrow" in type.FamilyName


"""
Analyzer class

"""


class TagCollisionInViewAnalzyer(Analyzer):
    name = NAME
    _author = AUTHOR

    def analyze(self, data, **kwargs):
        if isinstance(data, DB.Element):
            data = [data]
        view_ids = map(lambda view: view.Id, data)
        ignore_arrows = kwargs.get(
            "Ignore Flow Direction Arrows",
            DEFAULT_ARGS["Ignore Flow Direction Arrows"])
        sensitivity = kwargs.get("Sensitivity", DEFAULT_ARGS["Sensitivity"])
        tags = list(
            DB.FilteredElementCollector(doc).OfClass(
                DB.IndependentTag).ToElements())
        if kwargs.get("Include Spatial Element Tags",
                      DEFAULT_ARGS["Include Spatial Element Tags"]):
            room_tags = list(
                DB.FilteredElementCollector(doc).OfClass(
                    DB.SpatialElementTag).ToElements())
            tags += room_tags

        def filter_tags(tag):
            result = True
            in_views = tag.OwnerViewId in view_ids
            result = result and in_views
            if ignore_arrows:
                is_arrow_symbol = is_flow_arrow(tag)
                result = result and not is_arrow_symbol
            return result

        tags = filter(filter_tags, tags)

        collision_analyzer = qa_engine.get_analyzer("tag_collision")
        return collision_analyzer.analyze(tags,
                                          sensitivity=sensitivity,
                                          **kwargs)


"""
Export the Analyzer class
"""
export = TagCollisionInViewAnalzyer()
