# -*- coding: utf-8 -*-
import copy
from enum import Enum
from pyrevit import script, DB

_logger = script.get_logger()
output = script.get_output()


def get_level_prefix(levels):
    # type: (list[int]) -> str
    """
    Returns a string with the given levels as a prefix.
    """
    return str.join(".", map(str, levels)) + " "


class ReportGroupType(Enum):
    """
    The type of the report section.
    Info: A collection of report items that are not tested. It works only as an indicator.
            For example: Count of all elements or count of families.
    Test: A collection of report items that are tested. It works as a test and shows the pass rate.
            For example: The elements with warnings.
    """
    INFO = "INFO"
    TEST = "TEST"


class ReportSection(object):
    """
    A report section is a collection of report itemss
    There are two types of report sections:
    1. INFO: A collection of report items that are not tested. It works only as an indicator.
       For example: Count of all elements or count of families.
    2. TEST: A collection of report items that are tested. It works as a test and shows the pass rate.
       For example: The elements with warnings.

    Attributes
    ----------
        name (str): The name of the report section
        description (str): The description of the report section
        items (list[ReportItem]): A list of report items
        group_type (ReportGroupType): The type of the report section. It can be INFO or TEST
        print_details (bool): If True, the details of every report item in this section will be printed
        max_printed_items (int): The maximum number of items to be printed if `print_details` is `True`
        passed_count (int): The number of items that are passed
        total_count (int): The total number of items
    """
    name = "Report Section"

    def __init__(self,
                 name,
                 description,
                 type=ReportGroupType.INFO,
                 print_details=True,
                 **kwargs):
        self.name = name
        self.description = description
        self.items = []
        self.children_sections = []
        self._group_type = type
        self.print_details = print_details
        self.max_printed_items = 20
        self.__kwargs = kwargs
        self.__passed_count = None
        self.__total_count = None

    def add_item(self, item):
        # type: (ReportItem) -> None
        if not isinstance(item, ReportItem):
            raise Exception(
                "ReportGroup.item() only accepts ReportItem objects")
        self.items.append(item)

    @property
    def failed_items(self):
        # type: () -> list[ReportItem]
        """Returns a list of items that are not passed"""
        return [item for item in self.items if item.passed == False]

    @property
    def name(self):
        # type: () -> str
        """Returns the name of the report section"""
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def description(self):
        # type: () -> str
        """Returns the description of the report section"""
        return self._description

    @description.setter
    def description(self, value):
        self._description = value

    @property
    def passed_count(self):
        if self.__passed_count is None:
            return len(self.items) - len(self.failed_items)
        else:
            return self.__passed_count

    @passed_count.setter
    def passed_count(self, value):
        self.__passed_count = value

    @property
    def total_count(self):
        if self.__total_count is None:
            return len(self.items)
        else:
            return self.__total_count

    @total_count.setter
    def total_count(self, value):
        self.__total_count = value

    @property
    def group_type(self):
        # type: () -> ReportGroupType
        """
        Returns the type of the report section
        There are two types of report sections:
        1. `INFO`: A collection of report items that are not tested. It works only as an indicator.
            For example: Count of all elements or count of families.
        2. `TEST`: A collection of report items that are tested. It works as a test and shows the pass rate.
            For example: The elements with warnings.
        """
        return self._group_type

    def __calculate_passed_ratio(self, passed_count=None, total_count=None):
        # type: (float, float) -> float
        passed_count = passed_count or len(self.items) - len(self.failed_items)
        total_count = total_count or len(self.items)

        passed_count = float(passed_count)
        total_count = float(total_count)

        if total_count == 0:
            return 0.0

        if total_count < passed_count:
            _logger.warning(
                "Passed count is larger than total count. Passed count: {passed_count:.2f}, Total count: {total_count:.2f}"
                .format(passed_count=passed_count, total_count=total_count))
            return 1.0

        ratio = passed_count / total_count
        return ratio

    @property
    def passed_ratio(self):
        # type: () -> float
        """
        Returns the passed ratio of the report section.
        """
        return self.__calculate_passed_ratio(self.passed_count,
                                             self.total_count)

    @passed_ratio.setter
    def passed_ratio(self, value):
        self.passed_count = 100.0 * value
        self.total_count = 100.0

    @property
    def all_items(self):
        """
        A list of all report items in this report section and all children report sections.
        """
        items = self.items[:]
        for section in self.children_sections:
            items += section.all_items
        return items

    def print_report(self, title_prefix="", levels=[1]):
        # type: (str, list[int]) -> None
        """
        Prints the report of the report section.

        Parameters
        ----------
            title_prefix (str): The prefix of the title of the report section. It's usually the index number of the report section.
        """
        levels = list(levels)
        title = ""
        for _ in range(len(levels)):
            title += "#"
        title += " {level} {prefix}{title}".format(
            level=get_level_prefix(levels),
            prefix=title_prefix,
            title=self.name)

        # Add "Select All" to the title
        if self.group_type == ReportGroupType.TEST:
            report_items = [
                item for item in self.all_items if item.passed == False
            ]
        elif self.group_type == ReportGroupType.INFO:
            report_items = self.all_items
        if len(report_items) > 0:
            element_ids = set()
            for item in report_items:
                element_ids.update(item.element_ids)
            element_ids = [
                DB.ElementId(int(id)) for id in element_ids if id.isdigit()
            ]
            title += " " + output.linkify(
                element_ids, "Select All Related {count} Elements".format(
                    count=len(element_ids)))

        output.print_md(title)
        output.print_md("{}".format(self.description))
        if self.group_type == ReportGroupType.TEST:
            output.print_md("**Passed: {:.2f}% ** ({}/{})".format(
                self.passed_ratio * 100, self.passed_count, self.total_count))
        elif self.group_type == ReportGroupType.INFO and len(self.items) > 0:
            output.print_md("**Count:** {}".format(self.total_count))
        if self.print_details and len(self.items) > 0:
            table_data = [item.get_table_data() for item in self.items]
            output.print_md("**Details:**")
            if len(table_data) > self.max_printed_items:
                output.print_md(
                    "*Too many items to show. Showing first {count} items.*".
                    format(count=self.max_printed_items))
                table_data = table_data[:self.max_printed_items]
            output.print_table(
                table_data,
                columns=["Result", "Name", "Element ID", "Description"],
            )

        children_level = levels + [0]
        for section in self.children_sections:
            children_level[-1] += 1
            section.print_report(levels=children_level)

    def decorate_self(self, func, deep_copy=False):
        # type: (function, bool) -> ReportSection
        """
        Decorate the report section and all children report sections with a function.
        """
        if deep_copy:
            copied_self = func(copy.deepcopy(self))
        else:
            copied_self = func(self)
        copied_self.children_sections = [
            section.map_self(func, deep_copy=False)
            for section in self.children_sections
        ]
        return copied_self

    def decorate_items(self, func):
        # type: (function) -> ReportSection
        """
        Decorate the report items in this report section and all children report sections with a function.
        """
        self.items = [func(item) for item in self.items]
        for section in self.children_sections:
            section.decorate_items(func)
        return self


class ReportItem(object):
    """
    A report item is a single item in a report section.
    It usually associates with an element in the model.
    """

    def __init__(self, name, element_ids=[], description="", passed=None):
        self.name = name
        if not isinstance(element_ids, list):
            element_ids = [element_ids]
        self.element_ids = map(str, element_ids)
        self.description = description
        self.passed = passed

    def show_element(self):
        # type: () -> None
        _logger.warning(
            "function `show_element` not implemented yet. Element IDs: {id}".
            format(id=str.join(", ", self.element_ids)))

    def __iter__(self):
        return iter(
            [self.passed, self.name, self.element_ids, self.description])

    def get_table_data(self):
        # type: () -> list[str]
        result = u" "
        if self.passed == True:
            # ICON: :heavy_check_mark: :white_circle:
            result = md_html(u"\U00002714 passed", "color:green;height:14pt;")
        if self.passed == False:
            # ICON: :cross_mark:
            result = md_html(u"**\U0001F534 FAILED**",
                             "color:red;height:14pt;")
        element_id_links = output.linkify(
            [DB.ElementId(int(id)) for id in self.element_ids if id.isdigit()])
        return [
            result, self.name, element_id_links
            or str.join(", ", self.element_ids), self.description
        ]


def md_html(content, styles):
    # type: (str, str) -> str
    """
    Returns a string with the content wrapped in a span with the given styles
    """
    return '<span style="{styles}">{content}</span>'.format(styles=styles,
                                                            content=content)


def print_reports(name, report_sections, description="", level=[1]):
    # type: (str, list[ReportSection], str, list[int]) -> None
    """
    Print a list of report groups
    """
    report_title = ""
    for _ in range(len(level)):
        report_title += "#"

    report_title += " {prefix} {name}".format(prefix=get_level_prefix(level),
                                              name=name)

    output.print_md(report_title)
    output.print_md(description)
    level = list(level)
    level.append(0)
    for group in report_sections:
        level[-1] += 1
        if isinstance(group, ReportSection):
            group.print_report(levels=level)
        elif isinstance(group, list):
            if len(group) == 1:
                group[0].print_report(levels=level)
            else:
                print_reports(name + " (subreport)", group, level=level + [1])
        # if hasattr(group,"items") and not group.items:
        #     output.print_md(md_html(u"\U00002714 all good!", "color:green"))
        output.insert_divider(' ')
    output.show()
