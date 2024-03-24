from qa_engine import Analyzer
from qa_report import ReportSection, ReportItem, ReportGroupType
from pyrevit import HOST_APP, EXEC_PARAMS
from pyrevit import revit, DB, UI
from pyrevit import script
from pyrevit.forms import ProgressBar
"""
Constants

"""
NAME = 'Boundingbox Collision Analyzer'
DESCRIPTION = """
This analyzer receives a list of elements and checks if there are any boundingbox collisions between them.
However, it's not suitable for checking 2D elements like tags.
"""
AUTHOR = 'Junfeng Xiao'

ARG_TYPES = {
    'sensitivity': float,
}

DEFAULT_ARGS = {
    'sensitivity': 0.8,
}

HIDDEN = True
"""
Environment variables

"""
doc = revit.doc
uidoc = HOST_APP.uidoc
logger = script.get_logger()
output = script.get_output()


def _default_fn_get_bb(element):
    return element.get_BoundingBox(None)


def get_middle_point(bb):
    """
    Get the middle point of the element.
    """
    return (bb.Max + bb.Min) / 2


def get_elements_around(base_element,
                        elements,
                        distance_factor=10,
                        fn_get_bb=_default_fn_get_bb):
    """
    Get elements around the base element by a given distance factor.
    elements: other elements to be checked
    """
    bb = fn_get_bb(base_element)
    base_point = get_middle_point(bb)
    base_distance = bb.Max.DistanceTo(bb.Min)
    distance = base_distance * distance_factor
    elements_around = []
    for element in elements:
        if element.Id == base_element.Id:
            continue
        point = get_middle_point(fn_get_bb(element))
        if point.DistanceTo(base_point) < distance:
            elements_around.append(element)
    return elements_around


def get_clashed_elements(base_element,
                         elements,
                         view=None,
                         tolerance=1e-6,
                         sensitivity=DEFAULT_ARGS["sensitivity"],
                         fn_get_bb=_default_fn_get_bb):
    """
    Get elements that are clashed with the base element.
    """
    base_bb = fn_get_bb(base_element)
    base_outline = DB.Outline(base_bb.Min, base_bb.Max)
    if base_outline.IsScaleValid(sensitivity):
        base_outline.Scale(sensitivity)
    result = []
    for element in elements:
        if element.Id == base_element.Id:
            continue
        element_bb = fn_get_bb(element)
        element_outline = DB.Outline(element_bb.Min, element_bb.Max)
        if element_outline.IsScaleValid(sensitivity):
            element_outline.Scale(sensitivity)
        if base_outline.Intersects(element_outline, tolerance):
            result.append(element)
    return result


def create_clash_report_item(first, second):
    """
    Create a report item for a list of elements.
    """
    element_type_first = first.Category.Name
    element_type_second = second.Category.Name
    if element_type_first == element_type_second:
        element_type_text = "{element_type}".format(
            element_type=element_type_first)
    else:
        element_type_text = "{element_type_first} and {element_type_second}".format(
            element_type_first=element_type_first,
            element_type_second=element_type_second)
    item = ReportItem(
        name="Clash between {element_type}".format(
            element_type=element_type_text),
        description="Clash between {first_type} and {second_type}".format(
            first_type=element_type_first,
            # first_id= output.linkify(first.Id),
            second_type=element_type_second,
            # second_id= output.linkify(second.Id)
        ),
        element_ids=[e.Id.IntegerValue for e in [first, second]],
        passed=False)
    return item


def element_has_bb(element, fn_get_bb=_default_fn_get_bb):
    """
    Check if the element has a bounding box.
    """
    if fn_get_bb(element) is None:
        logger.warn("Element {element_id} has no bounding box.".format(
            element_id=output.linkify(element.Id)))
        return False
    return True


"""
Analyzer class

"""


class BoundingboxCollisionAnalyzer(Analyzer):
    name = NAME
    _author = 'Junfeng Xiao'

    def analyze(self, data, **kws):
        desc = DESCRIPTION
        desc += " through {count} elements".format(count=len(data))
        kwargs = DEFAULT_ARGS.copy()
        kwargs.update(kws)
        section = ReportSection(name=NAME,
                                description=desc,
                                type=ReportGroupType.TEST,
                                print_details=True)
        fn_get_bb = kwargs.get("fn_get_bb", _default_fn_get_bb)

        tolerance = 1e-6
        sensitivity = kwargs["sensitivity"]

        # filter elements with no bounding box
        data = filter(fn_get_bb, data)

        section.total_count = len(data)

        clashes = set()
        failed_elements = set()
        for idx, element in enumerate(data):
            if element is None:
                continue
            elements_around = get_elements_around(element,
                                                  data,
                                                  fn_get_bb=fn_get_bb)
            clashed_elements = get_clashed_elements(element,
                                                    elements_around,
                                                    fn_get_bb=fn_get_bb,
                                                    tolerance=tolerance,
                                                    sensitivity=sensitivity)
            if clashed_elements:
                for clashed_element in clashed_elements:
                    ele_id = element.Id.IntegerValue
                    clashed_ele_id = clashed_element.Id.IntegerValue
                    # Skip if the clash has been reported
                    if not frozenset([ele_id, clashed_ele_id]) in clashes:
                        item = create_clash_report_item(
                            element, clashed_element)
                        failed_elements.update([ele_id, clashed_ele_id])
                        section.add_item(item)
                        clashes.add(frozenset([ele_id, clashed_ele_id]))
        section.passed_count = section.total_count - len(failed_elements)
        return section


export = BoundingboxCollisionAnalyzer()
