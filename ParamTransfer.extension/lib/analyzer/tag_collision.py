from calendar import c
from qa_engine import Analyzer, get_analyzer
from qa_report import ReportSection, ReportItem, ReportGroupType
from pyrevit import HOST_APP, EXEC_PARAMS, _HostApplication
from pyrevit import revit, DB, UI
from pyrevit import script
from pyrevit.forms import ProgressBar

NAME = 'Check if tags overlap'
DESCRIPTION = """
This analyzer receives a list of tag elements and checks if there's any tag overlapping between them.
Sensitivity is a value between 0 and 1. The bigger the value, the more sensitive the analyzer is.
You can also choose to report the bounding box error of tags (for ghost tags).
"""

doc = revit.doc
uidoc = HOST_APP.uidoc
logger = script.get_logger()
output = script.get_output()
hostapp = _HostApplication()

boundingbox_collision_analyzer = get_analyzer("boundingbox_collision")

ARG_TYPES = {
    'sensitivity': float,
    'report bounding box error': bool,
    "report section name": str,
}

DEFAULT_ARGS = {
    'sensitivity': 0.5,
    'report bounding box error': True,
    "report section name": NAME,
}


def create_initial_report_item(element):
    """
    Create a report item for a list of elements.
    """
    element_type = element.Category.Name
    item = ReportItem(
        name="Tag {element_type}".format(element_type=element_type),
        description="",
        element_ids=[element.Id.IntegerValue],
        passed=True,
    )
    return item


def hide_tag_leader_lines(elements):
    """
    Hide tag leader lines.
    """
    transaction = DB.Transaction(doc, "Hide Leader Lines")
    transaction.Start()
    for element in elements:
        element.HasLeader = False
    transaction.Commit()


def get_middle_point(bb):
    """
    Get the middle point of the element.
    """
    return (bb.Max + bb.Min) / 2


def get_tag_bounding_box(tag, view=None):
    bb = tag.get_BoundingBox(view)
    if bb is None:
        return None
    else:
        bb.Min = DB.XYZ(bb.Min.X, bb.Min.Y, 0)
        bb.Max = DB.XYZ(bb.Max.X, bb.Max.Y, 1)
        return bb


_cache_tag_real_bb = {}
_cache_tag_bb_with_leader = {}
_cache_tag_bb_head = {}


def clear_cache():
    _cache_tag_real_bb.clear()
    _cache_tag_bb_with_leader.clear()
    _cache_tag_bb_head.clear()


def get_tag_refs(tag):
    if hostapp.is_newer_than(2021):
        return tag.GetTaggedReferences()
    else:
        return [tag.GetTaggedReference()]


def get_tag_leader_end(tag, tag_ref=None):
    if hostapp.is_newer_than(2021):
        return tag.GetLeaderEnd(tag_ref)
    else:
        return tag.LeaderEnd


def set_tag_leader_elbow(tag, tag_ref, leader_end_point):
    if hostapp.is_newer_than(2021):
        tag.SetLeaderElbow(tag_ref, leader_end_point)
    else:
        tag.LeaderElbow = leader_end_point


def precalculate_tag_bounding_boxes(elements, view):

    elements = filter(
        lambda e: e.HasLeader and e.OwnerViewId.IntegerValue == view.Id.
        IntegerValue, elements)

    for element in elements:
        _cache_tag_bb_with_leader[
            element.Id.IntegerValue] = get_tag_bounding_box(element, view)

    with RvtTransaction("Reset Tag Locations"):
        for tag in elements:
            tag_ref = get_tag_refs(tag)
            if tag_ref is None or len(tag_ref) == 0:
                continue
            tag_ref = tag_ref[0]
            tag.LeaderEndCondition = DB.LeaderEndCondition.Free
            leader_end_point = get_tag_leader_end(tag, tag_ref)
            tag.TagHeadPosition = leader_end_point
            set_tag_leader_elbow(tag, tag_ref, leader_end_point)

    for element in elements:
        _cache_tag_bb_head[element.Id.IntegerValue] = get_tag_bounding_box(
            element, view)


def calculate_real_bb(bb_with_leader, bb_head):
    # relative position of the tag head point to the tag bounding box
    head_on_top = False
    head_on_left = False
    tag_middle_point = get_middle_point(bb_with_leader)
    tag_header_middle_point = get_middle_point(bb_head)
    if tag_header_middle_point.Y < tag_middle_point.Y:
        head_on_top = True
    if tag_header_middle_point.X > tag_middle_point.X:
        head_on_left = True

    # estimate the tag head width and height
    tag_head_width = bb_head.Max.X - bb_head.Min.X
    tag_head_height = bb_head.Max.Y - bb_head.Min.Y
    real_tag_bb = bb_with_leader
    if head_on_top:
        real_tag_bb.Min = DB.XYZ(real_tag_bb.Min.X,
                                 real_tag_bb.Max.Y - tag_head_height,
                                 real_tag_bb.Min.Z)
    else:
        real_tag_bb.Max = DB.XYZ(real_tag_bb.Max.X,
                                 real_tag_bb.Min.Y + tag_head_height,
                                 real_tag_bb.Max.Z)

    if head_on_left:
        real_tag_bb.Max = DB.XYZ(real_tag_bb.Min.X + tag_head_width,
                                 real_tag_bb.Max.Y, real_tag_bb.Max.Z)
    else:
        real_tag_bb.Min = DB.XYZ(real_tag_bb.Max.X - tag_head_width,
                                 real_tag_bb.Min.Y, real_tag_bb.Min.Z)
    return real_tag_bb


def get_tag_real_bb(tag,
                    view,
                    bb_with_leader=None,
                    bb_head=None,
                    no_bb_element_list=None):
    """
    Get the real bounding box of the tag, excluding the leader line.
    Cache is used to improve performance.
    See discussion here: https://forums.autodesk.com/t5/revit-api-forum/tag-width-height-or-accurate-boundingbox-of-independenttag/td-p/8918658
    """
    if tag.Id.IntegerValue in _cache_tag_real_bb:
        return _cache_tag_real_bb[tag.Id.IntegerValue]

    if not tag.HasLeader:
        logger.debug("Tag {tag_id} has no leader.".format(
            tag_id=output.linkify(tag.Id)))
        return get_tag_bounding_box(tag, view)
    tag_ref = get_tag_refs(tag)
    if tag_ref is None or len(tag_ref) == 0:
        _cache_tag_real_bb[tag.Id.IntegerValue] = get_tag_bounding_box(
            tag, view)
        return get_tag_bounding_box(tag, view)
    tag_ref = tag_ref[0]

    if bb_with_leader is None:
        if tag.Id.IntegerValue in _cache_tag_bb_with_leader:
            bb_with_leader = _cache_tag_bb_with_leader[tag.Id.IntegerValue]
        else:
            bb_with_leader = get_tag_bounding_box(tag, view)

    if bb_head is None:
        if tag.Id.IntegerValue in _cache_tag_bb_head:
            bb_head = _cache_tag_bb_head[tag.Id.IntegerValue]
        else:
            with RvtTransaction("Get Tag Height") as t:
                tag.LeaderEndCondition = DB.LeaderEndCondition.Free
                leader_end_point = get_tag_leader_end(tag, tag_ref)
                tag.TagHeadPosition = leader_end_point
                set_tag_leader_elbow(tag, tag_ref, leader_end_point)
            bb_head = get_tag_bounding_box(tag, view)
            _cache_tag_bb_head[tag.Id.IntegerValue] = bb_head

    if bb_with_leader is None or bb_head is None:
        # logger.warn("Tag {tag_id} has no bounding box.".format(
        #     tag_id=output.linkify(tag.Id)))
        if no_bb_element_list is not None:
            no_bb_element_list.append(tag)
        return None
    real_tag_bb = calculate_real_bb(bb_with_leader, bb_head)
    _cache_tag_real_bb[tag.Id.IntegerValue] = real_tag_bb

    logger.debug("Tag {tag_id}:".format(tag_id=output.linkify(tag.Id)))
    logger.debug("Real Tag BB: {min} to {max}".format(min=real_tag_bb.Min,
                                                      max=real_tag_bb.Max))
    return real_tag_bb


class RvtTransaction:

    def __init__(self, name="Transaction", **kwargs):
        self.__transaction = DB.Transaction(doc, name)
        self.__kwargs = kwargs

    def __enter__(self):
        self.__transaction.Start()
        return self.__transaction

    def __exit__(self, type, value, traceback):
        if self.__transaction.HasStarted():
            if not self.__transaction.HasEnded():
                self.__transaction.Commit()


class TemporaryTransactionGroup:

    def __init__(self, name="Temporary Hide Leader Lines"):
        self.group = DB.TransactionGroup(doc, name)
        self.__rolled_back = False

    def __enter__(self):
        self.group.Start()
        return self.group

    def rollback(self):
        self.group.RollBack()
        self.__rolled_back = True

    def __exit__(self, type, value, traceback):
        if self.group.HasStarted():
            if not self.group.HasEnded():
                self.group.RollBack()
        if doc.IsWorkshared:
            # Relinquish the temporary modified elements
            options = DB.RelinquishOptions(True)
            DB.WorksharingUtils.RelinquishOwnership(doc, options, None)


class TagCollisionAnalyzer(Analyzer):
    name = NAME
    _author = 'Junfeng Xiao'

    def analyze(self, data, **kwargs):
        desc = DESCRIPTION
        desc += " through {count} elements".format(count=len(data))
        name = kwargs.get('report section name',
                          DEFAULT_ARGS['report section name'])
        section = ReportSection(name=name,
                                description=desc,
                                type=ReportGroupType.INFO,
                                auto_count=False,
                                print_details=True)

        # Bounding Box Error Section
        bb_section = None

        # tags with no bounding box
        bb_error_tags = None

        if kwargs.get('report bounding box error',
                      DEFAULT_ARGS['report bounding box error']):
            bb_section = ReportSection(name="Tag Bounding Box Error",
                                       description="Tag Bounding Box Error",
                                       type=ReportGroupType.TEST,
                                       auto_count=True,
                                       print_details=True)
            bb_section.max_printed_items = 200
            bb_error_tags = []

        view_ids = set()
        tolerance = kwargs.get('tolerance', 1e-6)
        sensitivity = kwargs.get('sensitivity', DEFAULT_ARGS['sensitivity'])

        for element in data:
            view_ids.add(element.OwnerViewId.IntegerValue)
        with ProgressBar(
                cancellable=True,
                title='Going through views... ({value} of {max_value})') as pb:
            with TemporaryTransactionGroup() as tg:
                i = 0
                for view_id in view_ids:
                    clear_cache()
                    i += 1

                    if pb.cancelled:
                        break
                    pb.update_progress(i, len(view_ids))

                    view = doc.GetElement(DB.ElementId(view_id))

                    # Filter 3D views
                    if view.ViewType == DB.ViewType.ThreeD:
                        continue

                    # view_id_link = output.linkify(view.Id, "{name}".format(name=view.Name))
                    logger.info("Processing view: {view_name}".format(
                        view_name=view.Name))

                    truncate_view_name = lambda name: "..." + name[50:] if len(
                        name) > 50 else name
                    # create report section for each view
                    view_section = ReportSection(
                        name="In view {name}".format(report=section.name,
                                                     name=truncate_view_name(
                                                         view.Name)),
                        description="In view `{name}`".format(
                            name=view.Name, ),
                        type=ReportGroupType.TEST,
                    )
                    view_section.max_printed_items = 100

                    elements_in_view = filter(
                        lambda element: element.OwnerViewId.IntegerValue ==
                        view_id, data)

                    section.passed_count = 0

                    # Start checking collision
                    precalculate_tag_bounding_boxes(elements_in_view, view)
                    view_result = boundingbox_collision_analyzer.analyze(
                        elements_in_view,
                        sensitivity=sensitivity,
                        tolerance=tolerance,
                        fn_get_bb=lambda e: get_tag_real_bb(
                            e, view, no_bb_element_list=bb_error_tags))
                    view_section.total_count = view_result.total_count
                    view_section.passed_count = view_result.passed_count
                    for item in view_result.items:
                        if item.passed:
                            view_section.passed_count += 1
                        else:
                            view_section.add_item(item)

                    if len(view_section.items) > 0:
                        section.children_sections.append(view_section)
                    else:
                        section.passed_count += 1
        if bb_section is not None:
            for tag in bb_error_tags:
                item = create_initial_report_item(tag)
                item.passed = False
                view = doc.GetElement(tag.OwnerViewId)
                # Tag Family and Type
                el_type = doc.GetElement(tag.GetTypeId())
                item.name = "{element_type}".format(
                    element_type=el_type.FamilyName or tag.Category.Name)
                item.description = "Element in view {view} has no bounding box!".format(
                    view=output.linkify(view.Id, view.Name))
                bb_section.add_item(item)
            if len(bb_section.items) > 0:
                section.children_sections.append(bb_section)

        return section


export = TagCollisionAnalyzer()
