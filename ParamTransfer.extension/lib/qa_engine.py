import imp
import pyrevit
from pyrevit import script, forms
from pyrevit import EXEC_PARAMS
from os import path
import traceback
import filemgr
import json
from enum import Enum
from functools import wraps

from qa_report import ReportSection, ReportItem

logger = script.get_logger()
engine_path = path.dirname(path.realpath(__file__))
collector_path = path.join(engine_path, "collector")
analyzer_path = path.join(engine_path, "analyzer")


def operator_default_kwargs_decorator(child_self, f):
    # type: (object, function) -> function
    @wraps(f)
    def wrapper(*args, **kwargs):
        logger.debug("calling self {}".format(child_self.__class__.__name__))
        kwargs_new = child_self.get_default_args()
        logger.debug("- args {}".format(args))
        kwargs_new.update(kwargs)
        logger.debug("- kwargs {}".format(kwargs_new))
        return f(*args, **kwargs_new)

    return wrapper


class _Operator(object):

    @property
    def logger(self):
        # type: () -> pyrevit.script.logger
        return script.get_logger()

    @property
    def module_type(self):
        # type: () -> ModuleType
        return None

    @property
    def author(self):
        # type: () -> str
        return self._author

    def __init__(self):
        self.name = self.name or self.__class__.__name__
        self._author = self._author or "BuroHappold"
        self.module_name = path.basename(self.__module__)

        if self.module_name.startswith(
                "{module_type}.".format(module_type=self.module_type)):
            self.module_name = self.module_name[len(self.module_type) + 1:]

        logger.debug("Initializing {module_type} '{module}' {name}".format(
            module_type=self.module_type,
            name=self.name,
            module=self.module_name))

    def get_default_args(self):
        # type: () -> dict
        if self.module_type is None:
            raise Exception("Module type is not defined")
        return self.__get_metadata_item(ModuleMeta.DEFAULT_ARGS, {})

    def get_arg_types(self):
        # type: () -> dict
        return self.__get_metadata_item(ModuleMeta.ARG_TYPES, {})

    def decorate_report_item(self, report_item):
        # type: (ReportItem) -> ReportItem
        return report_item

    def decorate_report_section(self, report_section):
        # type: (ReportSection) -> ReportSection
        return report_section

    def __get_metadata(self):
        module = get_module(self.module_name, self.module_type)
        if module is None:
            return {}
        else:
            return module.metadata

    def __get_metadata_item(self, key, default=None):

        return self.__get_metadata().get(key, default)

    def get_description(self, **kwargs):
        """
        Get a dynamic description of the operator based on the arguments.
        Return Default Description in metadata if not overridden.
        """
        return self.__get_metadata_item(ModuleMeta.DESCRIPTION,
                                        "(No description available)")

    @property
    def additional_settings_available(self):
        args = self.get_arg_types()
        return len(args) > 0

    def show_additional_settings(self, arg_values, **kwargs):
        # type: (dict, dict) -> dict
        """
        Show additional settings for the operator.
        Return a dict of arguments and their values if user clicks OK.
        Return None if user clicks Cancel.
        """
        from qa_ui.config_manager import OperationSettings

        args = self.get_default_args()
        args.update(arg_values)

        settings = OperationSettings(
            arg_values=args,
            metadata=self.__get_metadata(),
        )

        if settings.show():
            return settings.get_arg_values()
        else:
            return None

    def __str__(self):
        return "{module_type}: {name}".format(module_type=self.module_type,
                                              name=self.name)


class ScopeSelector(_Operator):
    """
    ScopeSelector is a class that collects Views as scope from the current Revit model.
    `Select` method should return a list of Revit View Elements.
    """

    # name = "Default Collector"
    # _author = "BuroHappold"

    def __init__(self):
        _Operator.__init__(self)
        self.select = operator_default_kwargs_decorator(self, self.select)

    def select(self, **kwargs):
        # type: (dict) -> list[pyrevit.revit.DB.Element]
        """Collect Elements and return them"""
        raise NotImplementedError("ScopeSelector.select() not implemented")

    def __iter__(self):
        return iter(self.select())

    def __call__(self, **kwargs):
        return self.select(**kwargs)

    @property
    def module_type(self):
        # type: () -> ModuleType
        return ModuleType.SCOPE_SELECTOR


class Collector(_Operator):
    """
    Collector is a class that collects Elements from the current Revit model.
    """

    # name = "Default Collector"
    # _author = "BuroHappold"

    def __init__(self):
        _Operator.__init__(self)
        logger.debug("Initializing collector {}".format(self.name))
        self.collect = operator_default_kwargs_decorator(self, self.collect)

    def collect(self, **kwargs):
        # type: (dict) -> list[pyrevit.revit.DB.Element]
        """Collect Elements and return them"""
        raise NotImplementedError("Collector.collect() not implemented")

    def __iter__(self):
        return iter(self.collect())

    def __call__(self, **kwargs):
        return self.collect(**kwargs)

    @property
    def module_type(self):
        # type: () -> ModuleType
        return ModuleType.COLLECTOR


class Analyzer(_Operator):
    """
    Analyzer is a class that analyzes the data (elements) collected by the Collector.
    """
    name = "Default Analyzer"
    _author = "BuroHappold"

    def __init__(self):
        _Operator.__init__(self)
        logger.debug("Initializing analyzer {}".format(self.name))
        self.analyze = operator_default_kwargs_decorator(self, self.analyze)

    def analyze(self, data, **kwargs):
        # type: (list[pyrevit.revit.DB.Element], dict) -> ReportSection
        """Analyze the data and return ReportSection object"""
        raise NotImplementedError("Analyzer.analyze() not implemented")

    @property
    def module_type(self):
        # type: () -> ModuleType
        return ModuleType.ANALYZER

    def __call__(self, data, **kwargs):
        return self.analyze(data, **kwargs)


class Operation(object):
    """
    Operation is a combination of a Collector and an Analyzer.
    It collects data from the model using the Collector and then analyzes the data using the Analyzer.
    Finally it returns a ReportSection object, where the ReportItem objects are stored.
    """
    name = "Default Operation"

    def __init__(self,
                 scope_selector,
                 collector,
                 analyzer,
                 scope_selector_kwargs=None,
                 collector_kwargs=None,
                 analyzer_kwargs=None,
                 name=None):
        self.name = name or self.name
        if isinstance(scope_selector, str):
            scope_selector = get_scope_selector(scope_selector)
        if isinstance(collector, str):
            collector = get_collector(collector)
        if isinstance(analyzer, str):
            analyzer = get_analyzer(analyzer)

        if not isinstance(scope_selector, ScopeSelector):
            raise TypeError(
                "ScopeSelector must be a ScopeSelector or a string")
        if not isinstance(collector, Collector):
            raise TypeError("Collector must be a Collector or a string")
        if not isinstance(analyzer, Analyzer):
            raise TypeError("Analyzer must be an Analyzer or a string")

        self.scope_selector = scope_selector
        self.collector = collector
        self.analyzer = analyzer
        self.scope_selector_kwargs = scope_selector_kwargs or {}
        self.collector_kwargs = collector_kwargs or {}
        self.analyzer_kwargs = analyzer_kwargs or {}

    def run(self):
        # type: () -> ReportSection
        data = None
        result = None
        logger.debug("Running operation {}".format(self.__str__()))

        try:
            scope = self.scope_selector.select(**self.scope_selector_kwargs)
        except Exception as e:
            logger.error("Running operation {}".format(self.__str__()))
            logger.error("Error selecting scope in {}: {}".format(
                self.scope_selector.name, e))
            logger.error(
                "Please contact BIM team or its author {} for support.".format(
                    self.scope_selector.author))
            logger.error("Stack trace:\n" + traceback.format_exc())
            raise Exception(
                "Error selecting scope in {}".format(self.scope_selector.name),
                e)

        try:
            data = self.collector(scope=scope, **self.collector_kwargs)
        except Exception as e:
            logger.error("Running operation {}".format(self.__str__()))
            logger.error("Error collecting data in {}: {}".format(
                self.collector.name, e))
            logger.error(
                "Please contact BIM team or its author {} for support.".format(
                    self.collector.author))
            logger.error("Stack trace:\n" + traceback.format_exc())
            raise Exception(
                "Error collecting data in {}".format(self.collector.name), e)
        try:
            result = self.analyzer.analyze(data, **self.analyzer_kwargs)
        except Exception as e:
            logger.error("Running operation {}".format(self.__str__()))
            logger.error("Error analyzing data in {}: {}".format(
                self.analyzer.name, e))
            logger.error(
                "Please contact BIM team or its author {} for support.".format(
                    self.analyzer.author))
            logger.error("Stack trace:\n" + traceback.format_exc())
            raise Exception(
                "Error analyzing data in {}".format(self.analyzer.name), e)

        if isinstance(result, ReportSection) and len(self.name) > 1:
            result.name = self.name
        # Check if decorator functions are overridden

        ## Check report section decorator
        operators = [self.scope_selector, self.collector, self.analyzer]
        for operator in operators:
            if operator.decorate_report_section.__func__ != operator.decorate_report_section.__func__:
                logger.info("{} {} overrides decorate_report_section".format(
                    operator.module_type, operator.name))
                result = operator.decorate_report_section(result)

            if operator.decorate_report_item.__func__ != operator.decorate_report_item.__func__:
                logger.info("{} {} overrides decorate_report_item".format(
                    operator.module_type, operator.name))
                result = result.decorate_items(operator.decorate_report_item)

        return result

    def __str__(self):
        return "{operation}:{scope} -> {collector} -> {analyzer}".format(
            scope=self.scope_selector.name,
            operation=self.name,
            collector=self.collector.name,
            analyzer=self.analyzer.name)

    def __call__(self):
        return self.run()


class OperationSet(object):

    def __init__(self,
                 name="Default Operation Set",
                 description="",
                 operations=None):
        # type: (str, str, list[Operation]) -> None
        self.name = name
        self.description = description
        # type: list[Operation]
        self.operations = operations or []

    def load_operations(self, operations, preserve_existing=False):
        # type: (list[Operation], bool) -> None
        if not preserve_existing:
            self.operations = []
        self.operations.extend(operations)

    def to_config(self):
        # type: () -> dict
        """Return a config dict"""
        return filemgr.JsonParser.from_operation_set(self)

    def to_config_str(self, pretty_print=True):
        # type: (bool) -> str
        """Return a string containing a JSON config"""
        config = self.to_config()
        if pretty_print:
            indent = 4
        else:
            indent = None
        return json.dumps(config, indent=indent)

    def to_config_file(self, config_file_path, pretty_print=True):
        # type: (str, bool) -> None
        """Save a JSON config to a file"""
        config_str = self.to_config_str(pretty_print)
        with open(config_file_path, "w") as f:
            f.write(config_str)

    @staticmethod
    def from_config(config):
        # type: (dict) -> OperationSet
        """Load OperationSet from a config dict"""
        return filemgr.JsonParser.to_operation_set(config)

    @staticmethod
    def from_config_str(config_str):
        # type: (str) -> OperationSet
        """Load OperationSet from a string containing a JSON config"""
        config = json.loads(config_str)
        return OperationSet.from_config(config)

    @staticmethod
    def from_config_file(config_file_path):
        # type: (str) -> OperationSet
        """Load OperationSet from a JSON config file"""
        with open(config_file_path, "r") as f:
            config = json.load(f)
        return OperationSet.from_config(config)

    def run(self):
        # type: () -> list[ReportSection]
        results = []
        for operation in self.operations:
            results.append(operation.run())
        return results


def get_available_modules(subpath, show_hidden=False):
    """Get all modules in the given subpath of the current command path"""
    import os
    from os import path

    basepath = path.join(engine_path, subpath)
    module_names = []
    for module_name in os.listdir(basepath):
        if path.isfile(path.join(basepath,
                                 module_name)) and module_name.endswith(".py"):
            try:
                module_name = module_name[:-3]
                module = _load_module(module_name, subpath)
                if module is not None and (
                        show_hidden
                        or not module.metadata.get("HIDDEN", False)):
                    module_names.append(module_name)
            except Exception as e:
                logger.warn(
                    "Error loading module {path}\{module}: {error}".format(
                        module=module_name, path=basepath, error=e))
                logger.warn("Stack trace:\n" + traceback.format_exc())
    return module_names


__module_cache = {}


class ModuleType(str, Enum):
    COLLECTOR = "collector"
    ANALYZER = "analyzer"
    SCOPE_SELECTOR = "scope_selector"


class ModuleMeta(str, Enum):
    NAME = "NAME"
    DESCRIPTION = "DESCRIPTION"
    AUTHOR = "AUTHOR"
    RETURN = "RETURN"
    ARG_TYPES = "ARG_TYPES"
    DEFAULT_ARGS = "DEFAULT_ARGS"
    MODULE_NAME = "MODULE_NAME"
    HIDDEN = "HIDDEN"


def _load_module(module_name, subpath):
    # type: (str, ModuleType) -> object
    """Get a module by name in the given subpath of the current command path"""
    import imp
    import os
    # from importlib import import_module
    # module = import_module("{}.{}".format(subpath, module_name))
    module_path = os.path.join(engine_path, subpath, module_name + ".py")

    if module_path in __module_cache:
        return __module_cache[module_path]

    module = imp.load_source(
        "{part}.{module}".format(part=subpath, module=module_name),
        module_path)

    # Add metadata to module
    module.__dict__["metadata"] = __get_module_metadata(
        module, module_name=module_name)

    # cache module
    __module_cache[module_path] = module

    return module


def get_scope_selector(scope_selector_name):
    # type: (str) -> ScopeSelector
    """Get a scope selector by name"""
    try:
        return _load_module(scope_selector_name,
                            ModuleType.SCOPE_SELECTOR).export
    except Exception as e:
        stack = traceback.format_exc()
        logger.error("Error loading {path} '{module}':\n {error}".format(
            module=scope_selector_name,
            path=ModuleType.SCOPE_SELECTOR,
            error=e))
        logger.error("Stack trace for debugging:\n" + stack)


def get_collector(collector_name):
    # type: (str) -> Collector
    """Get a collector by name"""
    try:
        return _load_module(collector_name, ModuleType.COLLECTOR).export
    except Exception as e:
        stack = traceback.format_exc()
        logger.error("Error loading {path} '{module}':\n {error}".format(
            module=collector_name, path=ModuleType.COLLECTOR, error=e))
        logger.error("Stack trace for debugging:\n" + stack)
        return StubCollector(e, stack, collector_name)


def get_analyzer(analyzer_name):
    # type: (str) -> Analyzer
    """Get an analyzer by name"""
    try:
        return _load_module(analyzer_name, ModuleType.ANALYZER).export
    except Exception as e:
        stack = traceback.format_exc()
        logger.error("Error loading {path} '{module}':\n {error}".format(
            module=analyzer_name, path=ModuleType.ANALYZER, error=e))
        logger.error("Stack trace for debugging:\n" + stack)
        return StubAnalyzer(e, stack, analyzer_name)


def get_module(module_name, module_type):
    # type: (str, ModuleType) -> object
    """Get a module by name and type"""
    try:
        return _load_module(module_name, module_type)
    except Exception as e:
        stack = traceback.format_exc()
        logger.error("Error loading {path} '{module}':\n {error}".format(
            module=module_name, path=module_type, error=e))
        logger.error("Stack trace for debugging:\n" + stack)
        return None


def __get_module_metadata(module, module_name=None):
    # type: (object, str) -> dict
    """Get metadata for a module"""
    module_dict = module.__dict__
    module_name = module_name or module.__name__
    metadata = {
        ModuleMeta.NAME:
        module_dict.get(ModuleMeta.NAME.value, module_name),
        ModuleMeta.DESCRIPTION:
        module_dict.get(ModuleMeta.DESCRIPTION.value, ""),
        ModuleMeta.AUTHOR:
        module_dict.get(ModuleMeta.AUTHOR.value, module.export.author),
        ModuleMeta.RETURN:
        module_dict.get(ModuleMeta.RETURN.value, ""),
        ModuleMeta.ARG_TYPES:
        module_dict.get(ModuleMeta.ARG_TYPES.value, {}),
        ModuleMeta.DEFAULT_ARGS:
        module_dict.get(ModuleMeta.DEFAULT_ARGS.value, {}),
        ModuleMeta.MODULE_NAME:
        module_name,
        ModuleMeta.HIDDEN:
        module_dict.get(ModuleMeta.HIDDEN.value, False),
    }
    return metadata


"""
 Error Handling
"""


class StubCollector(Collector):
    name = ""
    _author = "engine"

    def __init__(self, error, stack_trace, name=""):
        self.error = error
        self.stack_trace = stack_trace
        self.name = name

    def collect(self, **kwargs):
        message = "Stub Collector is used to replace a collector that failed to load."\
            "This is a temporary solution to prevent the QA extension from crashing."\
            "Please read the PREVIOUS ERROR MESSAGE to find out why collector{name} failed to load.".format(
                name=" \"" + self.name + "\"" if self.name != "" else "")
        logger.warn(message)
        expended_message = ""
        if self.error is not None:
            err_msg = "For your convenience, here's a copy of the real error:\n {}".format(
                self.error)
            logger.error(err_msg)
            expended_message += err_msg

        if self.stack_trace is not None:
            stack_trace_msg = "\nAnd here's a copy of the stack trace:\n {}".format(
                self.stack_trace)
            logger.error(stack_trace_msg)
            expended_message += stack_trace_msg

        if expended_message == "":
            expended_message = None

        forms.alert(message,
                    title="{name}: Something's Wrong".format(name=self.name),
                    expended_message=expended_message)
        return None


class StubAnalyzer(Analyzer):
    name = ""
    _author = "engine"

    def __init__(self, error, stack_trace, name=""):
        self.error = error
        self.stack_trace = stack_trace
        self.name = name

    def analyze(self, data, **kwargs):
        message = "Stub Analyzer is used to replace an analyzer that failed to load."\
            "This is a temporary solution to prevent the QA extension from crashing."\
            "Please read the PREVIOUS ERROR MESSAGE to find out why analyzer{name} failed to load.".format(
                name=" \"" + self.name + "\"" if self.name != "" else "")
        logger.warn(message)
        expended_message = ""
        if self.error is not None:
            err_msg = "For your convenience, here's a copy of the real error:\n {}".format(
                self.error)
            logger.error(err_msg)
            expended_message += err_msg

        if self.stack_trace is not None:
            stack_trace_msg = "\nAnd here's a copy of the stack trace:\n {}".format(
                self.stack_trace)
            logger.error(stack_trace_msg)
            expended_message += stack_trace_msg

        if expended_message == "":
            expended_message = None

        forms.alert(message,
                    title="{name}: Something's Wrong".format(name=self.name),
                    expended_message=expended_message)
        return []


def initialize():
    # type: () -> None
    """Initialize QA Engine"""

    # copy built-in configs to user config path if they don't exist
    import shutil
    import os
    from os import path
    from qa_ui.config_manager import CONFIG_EXTENSION, get_config_folder

    config_folder = get_config_folder()
    builtin_config_path = path.join(engine_path, "builtin_config")
    # get built-in config files including nested files
    builtin_config_files = []
    for root, dirs, files in os.walk(builtin_config_path):
        for file in files:
            if file.lower().endswith(CONFIG_EXTENSION):
                builtin_config_files.append(path.join(root, file))
    # copy built-in config files to user config path if they don't exist
    # and ensure subfolders exist
    for file in builtin_config_files:
        rel_path = path.relpath(file, builtin_config_path)
        dest_path = path.join(config_folder, rel_path)
        dest_dir = path.dirname(dest_path)
        if not path.exists(dest_dir):
            os.makedirs(dest_dir)
        if not path.exists(dest_path):
            shutil.copyfile(file, dest_path)


initialize()