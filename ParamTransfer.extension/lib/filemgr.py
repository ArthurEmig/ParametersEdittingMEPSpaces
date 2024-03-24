import pyrevit
from pyrevit import script
from pyrevit import EXEC_PARAMS
import qa_engine
import os
from os import path
from enum import Enum
import json

logger = script.get_logger()
engine_path = path.dirname(path.realpath(__file__))
collector_path = path.join(engine_path, "collector")
analyzer_path = path.join(engine_path, "analyzer")
builtin_config_path = path.join(engine_path, "config")


class ConfigType(str, Enum):
    """Config type"""
    OPERATION = "operation"
    OPERATION_SET = "operation_set"


def get_user_config_path():
    # type: () -> str
    """Get user config path"""
    appdata = os.getenv('APPDATA')
    config_path = path.join(appdata, "BH-QAEngine")
    # create config dirs
    if not path.exists(config_path):
        os.makedirs(config_path)
    return config_path


# User Config Path in AppData
user_config_path = get_user_config_path()


def save_config(config, filename):
    # type: (dict, str) -> dict
    """Save and overwrite config to file"""

    # parse new config to json

    if isinstance(config, qa_engine.Operation):
        config = JsonParser.from_operation(config)
    elif isinstance(config, list):
        try:
            config = JsonParser.from_operation_list(config)
        except:
            logger.debug("Failed to parse config to json: {}".format(config))
    elif isinstance(config, qa_engine.OperationSet):
        config = JsonParser.from_operation_set(config)

    with open(path.join(user_config_path, filename), "w") as file:
        json.dump(config, file, indent=4)
    return config


def load_config(filename):
    # type: (str) -> dict
    """Load config as dict from file"""

    if not path.exists(path.join(user_config_path, filename)):
        return {}
    else:
        with open(path.join(user_config_path, filename), "r") as file:
            return json.load(file)


def config_to_instance(config):
    """
    Convert config to ether operation or operation set
    """
    if not config.get("type"):
        raise KeyError("Config without type is not supported")

    if config["type"] == ConfigType.OPERATION:
        return JsonParser.to_operation(config)
    elif config["type"] == ConfigType.OPERATION_SET:
        return JsonParser.to_operation_set(config)
    else:
        raise KeyError("Config type {} is not supported".format(
            config["type"]))


def update_config(new_config, filename):
    # type: (dict, str) -> dict
    """Update config from file"""
    config = {}
    with open(path.join(user_config_path, filename), "r") as file:
        try:
            config = json.load(file)
        except:
            logger.debug(
                "Failed to load config from file: {}".format(filename))
    if isinstance(new_config, dict):
        config.update(new_config)
    elif isinstance(new_config, qa_engine.Operation):
        config.update(new_config)
    elif isinstance(config, list) and isinstance(new_config, list):
        try:
            config.extend(JsonParser.from_operation_list(new_config))
        except:
            config.extend(new_config)
    else:
        raise TypeError(
            "new_config must be dict, Operation, OperationList or list")
    return save_config(config, filename)


class JsonParser:
    """
    Parse configurations to xml file
    """

    @staticmethod
    def _get_module_info(module):
        # type: (qa_engine.Module) -> dict
        """Get module info, including name, author and module name"""
        return {
            "name": module.name,
            "author": module.author,
            "module_name": module.module_name,
        }

    @staticmethod
    def from_operation(operation):
        # type: (qa_engine.Operation) -> dict
        """Convert operation to json"""
        return {
            "type": ConfigType.OPERATION,
            "name": operation.name,
            "scope_selector":
            JsonParser._get_module_info(operation.scope_selector),
            "scope_selector_args": operation.scope_selector_kwargs,
            "collector": JsonParser._get_module_info(operation.collector),
            "collector_args": operation.collector_kwargs,
            "analyzer": JsonParser._get_module_info(operation.analyzer),
            "analyzer_args": operation.analyzer_kwargs,
        }

    @staticmethod
    def to_operation(json):
        # type: (dict) -> qa_engine.Operation
        """Convert json to operation"""
        if isinstance(json, str):
            json_dict = json.loads(json)
        elif isinstance(json, dict):
            json_dict = json
        else:
            raise TypeError("json must be either str or dict")
        scope_selector = qa_engine.get_scope_selector(
            json_dict.get("scope_selector", {}).get("module_name",
                                                    "current_view"))
        collector = qa_engine.get_collector(
            json_dict.get("collector", {}).get("module_name", "all_elements"))
        analyzer = qa_engine.get_analyzer(
            json_dict.get("analyzer", {}).get("module_name", "count_elements"))
        return qa_engine.Operation(
            name=json_dict["name"],
            scope_selector=scope_selector,
            collector=collector,
            analyzer=analyzer,
            scope_selector_kwargs=json_dict.get("scope_selector_args", {}),
            collector_kwargs=json_dict.get("collector_args", {}),
            analyzer_kwargs=json_dict.get("analyzer_args", {}))

    @staticmethod
    def from_operation_list(operations):
        # type: (list[qa_engine.Operation]) -> list[dict]
        """Convert operation list to json"""
        return [
            JsonParser.from_operation(operation) for operation in operations
        ]

    @staticmethod
    def to_operation_list(json):
        # type: (dict) -> list[qa_engine.Operation]
        """Convert json to operation list"""
        if isinstance(json, str):
            json_list = json.loads(json)
        elif isinstance(json, list):
            json_list = json
        else:
            raise TypeError("json must be either str or list")
        return [JsonParser.to_operation(json_dict) for json_dict in json_list]

    @staticmethod
    def from_operation_set(operation_set):
        # type: (qa_engine.OperationSet) -> dict
        """Convert operation set to json"""
        config = {
            "type": ConfigType.OPERATION_SET,
            "name": operation_set.name,
            "description": operation_set.description,
            "operations":
            JsonParser.from_operation_list(operation_set.operations)
        }
        return config

    @staticmethod
    def to_operation_set(json):
        # type: (dict) -> qa_engine.OperationSet
        """Convert json to operation set"""
        if isinstance(json, str):
            json_dict = json.loads(json)
        elif isinstance(json, dict):
            json_dict = json
        else:
            raise TypeError("json must be either str or dict")
        return qa_engine.OperationSet(
            name=json_dict.get("name", "Operation Set"),
            description=json_dict.get("description", ""),
            operations=JsonParser.to_operation_list(
                json_dict.get("operations", [])))
