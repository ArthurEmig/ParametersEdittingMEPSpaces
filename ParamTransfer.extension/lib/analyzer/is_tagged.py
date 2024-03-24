from qa_engine import Analyzer
from qa_report import ReportSection, ReportItem, ReportGroupType
from pyrevit import HOST_APP, EXEC_PARAMS
from pyrevit import revit, DB, UI
from pyrevit import script

import Autodesk.Revit.DB as db



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
NAME = 'Check if elements are tagged'
# Short description of the collector
DESCRIPTION = 'Check if elements are tagged'
# Author
AUTHOR = 'Arthur Emig'
# The arguments that could be passed to the analyzer
ARG_TYPES = {
    "Count Report Type": [t.value for t in ReportGroupType],
    "Print Details": bool,
    "Max Printed Items": int,
}
# Default values of arguments
DEFAULT_ARGS = {
    "Count Report Type": ReportGroupType.TEST.value,
    "Print Details": True,
    "Max Printed Items": 1000,
    "Collect elements in the active view only": True,

}

"""
Environment variables

"""
doc = revit.doc
uidoc = HOST_APP.uidoc
logger = script.get_logger()


"""
Analyzer class

"""
class IsTaggedAnalyzer(Analyzer):
    name = NAME
    _author = AUTHOR

    def analyze(self, data, **kwargs):
        desc = DESCRIPTION
        desc += " through {count} elements".format(count=len(data))
        section = ReportSection(name=NAME,
                                description=desc,
                                type=ReportGroupType.TEST,
                                auto_count=False,
                                print_details=True)
        report_type = kwargs.get("Count Report Type", DEFAULT_ARGS["Count Report Type"])
        print_details = kwargs.get("Print Details", DEFAULT_ARGS["Print Details"])
        max_printed_items = kwargs.get("Max Printed Items", DEFAULT_ARGS["Max Printed Items"])
        section = ReportSection(name=NAME,
                              description=desc,
                              type=ReportGroupType(report_type),
                              auto_count=True,
                              print_details=print_details)
        section.max_printed_items = max_printed_items
        only_in_active_view = kwargs["Collect elements in the active view only"]
        if only_in_active_view:
            activeview_id = doc.ActiveView.Id
        else:
            activeview_id = None
        for element in data:
            if element is None:
                continue

            name = "Unknown"
            if hasattr(element, "Name"):
                name = element.Name

            category = "Unknown"
            if element.Category:
                category = element.Category.Name

            item = ReportItem(
                name=name,
                description="{category} - {id}".format(
                    category=category,
                    id=element.Id.IntegerValue
                ),
                element_ids=[element.Id.IntegerValue],
                passed=is_tagged(elem=element, view_id=activeview_id),
            )
            section.add_item(item)

        # element_count = len(data)
        # if element_count > 0:
        #     section.passed_ratio = 1.0 - float(len(section.items)) / len(data)
        # else:
        #     section.passed_ratio = 1.0
        return section
    
def is_tagged(elem, view_id):
    """
    Check if the elememt (elem) has hosted independent tags.
    """
    filter_ = db.ElementClassFilter(db.IndependentTag)

    dependent_tags = elem.GetDependentElements(filter_)

    dependent_tags_viewids = [DB.Document.GetElement(doc,eid).OwnerViewId for eid in dependent_tags]

    if view_id not in dependent_tags_viewids:
        return False

    return bool(dependent_tags)

# def is_question_mark_in_tag_text(elem_id_list):

#     is_question_mark = False

#     # get tag elements
#     for elem_id in elem_id_list:
#         tag = doc.GetElemet(elem_id)
#         tag_text = tag.TagText
#         print(tag_text)





"""
Export the Analyzer class
"""
export = IsTaggedAnalyzer()
