from qa_engine import Analyzer
from qa_report import ReportSection, ReportItem, ReportGroupType
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
NAME = 'Count elements'
# Short description of the collector
DESCRIPTION = 'Count elements from the collector and list them in a table if Print Details is True.'
# Author
AUTHOR = 'Junfeng Xiao'
# The arguments that could be passed to the analyzer
ARG_TYPES = {
    "Count Report Type": [t.value for t in ReportGroupType],
    "Print Details": bool,
    "Max Printed Items": int,
}
# Default values of arguments
DEFAULT_ARGS = {
    "Count Report Type": ReportGroupType.INFO.value,
    "Print Details": True,
    "Max Printed Items": 20,
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
class CountAnalyzer(Analyzer):
    name = NAME
    _author = AUTHOR

    def analyze(self, data, **kwargs):
        report_type = kwargs.get("Count Report Type", DEFAULT_ARGS["Count Report Type"])
        print_details = kwargs.get("Print Details", DEFAULT_ARGS["Print Details"])
        max_printed_items = kwargs.get("Max Printed Items", DEFAULT_ARGS["Max Printed Items"])
        section = ReportSection(name=NAME,
                              description=DESCRIPTION,
                              type=ReportGroupType(report_type),
                              print_details=print_details)
        section.max_printed_items = max_printed_items
        for element in data:
            if element is None:
                continue

            name = "Unknown"
            if hasattr(element, "Name"):
                name = element.Name

            category = "Unknown"
            if hasattr(element, "Category") and hasattr(element.Category, "Name"):
                category = element.Category.Name

            item = ReportItem(
                name=name,
                description="{category} - {id}".format(
                    category=category,
                    id=element.Id.IntegerValue
                ),
                element_ids=[element.Id.IntegerValue],
            )
            section.add_item(item)
        return section

"""
Export the Analyzer class
"""
export = CountAnalyzer()
