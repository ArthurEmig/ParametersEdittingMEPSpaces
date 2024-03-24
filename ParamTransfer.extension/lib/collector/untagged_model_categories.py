from qa_engine import Collector
from pyrevit import HOST_APP, EXEC_PARAMS
from pyrevit import revit, DB, UI
from pyrevit import script,forms

"""
Environment variables
"""
doc = revit.doc
uidoc = HOST_APP.uidoc
logger = script.get_logger()


def get_categories():
    cat_names = []
    model_categories = doc.Settings.Categories
    for cat in model_categories:
        if cat.CategoryType == DB.CategoryType.Model:
            cat_names.append(cat.Name)
            # logger.error("Cate {cat} with type {type}".format(cat=cat.Name,type=cat.CategoryType))
    sorted_cat_names = sorted(cat_names)
    # logger.error("Cat names:")
    # logger.error(
    #     ", ".join(sorted_cat_names)
    # )
    return sorted_cat_names



"""
Constants
"""
# Human readable name of the collector
NAME = 'Collect model categories'
# Short description of the collector
DESCRIPTION = 'Collect all model categories exluding annotation and analytical categories'
# Return value type of the collector
RETURN = 'list[Element]'
# The arguments that could be passed to the collector
ARG_TYPES = {
    "Collect elements in the active view only": bool,
    "Categories to collect": get_categories(),
}
# Default values of arguments
DEFAULT_ARGS = {
    "Collect elements in the active view only": True,
    "Categories to collect": [],
}

HIDDEN = True



# def get_untagged_elements(elements_to_check):
def get_untagged_elements(elements_to_check, viewid):
    """
    This function receives a list of elements and return the untagged elements.
    """
    # defining ElementClassFilter that will be used in the check of dependent elements (tags) of elements. Room and Spaces have different to other element categories tag classes.
    tag_filter_rest = DB.ElementClassFilter(DB.IndependentTag)
    tag_filter_room = DB.Architecture.RoomTagFilter()
    tag_filter_space = DB.Mechanical.SpaceTagFilter()
    tag_filter_area = DB.AreaTagFilter()
    elements_with_no_tag = []
    
    for element in elements_to_check:
        dependent_tags_viewids = ([DB.Document.GetElement(doc,eid).OwnerViewId for eid in element.GetDependentElements(tag_filter_rest)] +
        [DB.Document.GetElement(doc,eid).OwnerViewId for eid in element.GetDependentElements(tag_filter_space)] +
        [DB.Document.GetElement(doc,eid).OwnerViewId for eid in element.GetDependentElements(tag_filter_room)] +
        [DB.Document.GetElement(doc,eid).OwnerViewId for eid in element.GetDependentElements(tag_filter_area)])
        if viewid not in dependent_tags_viewids:
            elements_with_no_tag.append(element)
    return elements_with_no_tag

"""
Collector class
"""
class UntaggedElementsCollector(Collector):
    name = NAME
    _author = 'Sergey Brezgin'

    def collect(self,**kwargs):
        # Get the Category Names
        category_names_to_check = kwargs["Categories to collect"]
        only_in_active_view = kwargs["Collect elements in the active view only"]
        elements = []
        all_categories = doc.Settings.Categories
        if only_in_active_view:
            activeview_id = doc.ActiveView.Id
        else:
            activeview_id = None

        for cat_name in category_names_to_check:
            # Category name To Category Class
            cat = next((c for c in all_categories if c.Name == cat_name),None)
            if cat is None:
                forms.alert("No category found with this name {name}".format(name=cat_name))
                raise ValueError("No category found with this name {name}".format(name=cat_name))
            # Category Class --> Elements in Category cat
            # collected_elements = FilteredElementCollector(doc,doc.ActiveView.Id).OfCategoryId(cat.Id).ToElements()
            collected_elements = DB.FilteredElementCollector(doc, activeview_id
            ).OfCategoryId(cat.Id).WhereElementIsNotElementType().ToElements()
            # Add elements of selected Category to the list
            elements.extend(collected_elements)
        
        # get untagged elements
        untagged_elemenets = get_untagged_elements(elements, activeview_id)
        return untagged_elemenets




"""
Export the collector class
"""
export = UntaggedElementsCollector()


