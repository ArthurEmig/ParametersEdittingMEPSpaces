from calendar import c
from qa_engine import Analyzer, get_analyzer
from qa_report import ReportSection, ReportItem, ReportGroupType
from pyrevit import HOST_APP, EXEC_PARAMS, _HostApplication
from pyrevit import revit, DB, UI
from pyrevit import script
from pyrevit.forms import ProgressBar

NAME = 'Check orphaned or unknown tags'
DESCRIPTION = 'Check orphaned tags (tag without host) or unknown tags (tag with question mark)'

doc = revit.doc
uidoc = HOST_APP.uidoc
logger = script.get_logger()
output = script.get_output()
hostapp = _HostApplication()

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


_cache_orphaned_tags = {}
_cache_unknown_tags = {}

def clear_cache():
    _cache_orphaned_tags.clear()
    _cache_unknown_tags.clear()

def get_tag_refs(tag):
    if isinstance(tag, DB.IndependentTag):
        if hostapp.is_newer_than(2021):
            return tag.GetTaggedReferences()
        else:
            return [tag.GetTaggedReference()]
    elif isinstance(tag, DB.Mechanical.SpaceTag):
        return [DB.Reference(tag.Space)]
    elif isinstance(tag, DB.Architecture.RoomTag):
        return [DB.Reference(tag.Room)]
    elif isinstance(tag, DB.AreaTag):
        return [DB.Reference(tag.Area)]
    else:
        return []

def get_bad_tags(elements, view):

    orphaned_tags = {}
    unknown_tags = {}

    elements = filter(
        lambda e: e.OwnerViewId.IntegerValue == view.Id.IntegerValue, elements)

    for tag in elements:
        tag_text = tag.TagText
        tag_ref_ids = [t.ElementId.IntegerValue for t in get_tag_refs(tag)]
        tag_ref_ishidden = [not doc.GetElement(r).IsHidden(view) for r in get_tag_refs(tag)]
        # if tag.GetTaggedReferences() is None or len(tag_ref_ids) == 0 or tag.IsOrphaned:
        if tag.IsOrphaned:
            orphaned_tags[tag] = "orphaned"
        elif tag_text == "" and any(tag_ref_ishidden):
            unknown_tags[tag] = tag_ref_ids
    return {"orphaned" : orphaned_tags,
            "unknown" : unknown_tags}
    
class TagContentAnalyzer(Analyzer):
    name = NAME
    _author = 'Michal Sobota'

    def analyze(self, data, **kwargs):
        desc = DESCRIPTION
        desc += " through {count} elements".format(count=len(data))
        section = ReportSection(name=NAME,
                                description=desc,
                                type=ReportGroupType.TEST,
                                auto_count=False,
                                print_details=True)
        # report_item_dict = {}
        view_ids = set()
        view_result = set()
        
        for element in data:
            view_ids.add(element.OwnerViewId.IntegerValue)
        with ProgressBar(cancellable=True, title='Going through views... ({value} of {max_value})') as pb:
            i = 0
            for view_id in view_ids:
                clear_cache()
                i += 1

                view = doc.GetElement(DB.ElementId(view_id))
                # Filter 3D views
                if view.ViewType == DB.ViewType.ThreeD:
                    continue
                # view_id_link = output.linkify(view.Id, "{name}".format(name=view.Name))
                logger.info("Processing view: {view_name}".format(
                    view_name=view.Name))
                elements_in_view = filter(
                    lambda element: element.OwnerViewId.IntegerValue == view_id, data)
                logger.debug("elements: ")
                logger.debug(output.linkify(
                    map(lambda e: e.Id, elements_in_view)))
                bad_tags = get_bad_tags(elements_in_view, view)
                
                for bad_tag in bad_tags["unknown"]:
                    item = ReportItem(
                        name="Unknown {element_type}.".format(
                            element_type=bad_tag.Category.Name),
                        description="view '{view}': The tag has unknown value. The tag's hosts IDs: {hosts_ids}.".format(
                            view=view.Name, hosts_ids=", ".join([str(t) for t in bad_tags["unknown"][bad_tag]])
                        ),
                        element_ids=[bad_tag.Id.IntegerValue],
                        passed=False
                    )
                    section.add_item(item)

                for bad_tag in bad_tags["orphaned"]:
                    item = ReportItem(
                        name="Orphaned {element_type}.".format(
                            element_type=bad_tag.Category.Name),
                        description="view '{view}': The tag is orphaned.".format(
                            view=view.Name),
                        element_ids=[bad_tag.Id.IntegerValue],
                        passed=False
                    )
                    section.add_item(item)
                
        element_count = len(data)
        if element_count > 0:
            section.passed_ratio = 1.0 - float(len(section.items)) / len(data)
        else:
            section.passed_ratio = 1.0
        
        section.max_printed_items = 100
        return section


export = TagContentAnalyzer()
