import copy
from math import log
import os
import stat
import traceback
from pyrevit import script, forms
from pyrevit import EXEC_PARAMS
from os import path
import filemgr
from enum import Enum
from pyrevit.forms import WPFWindow, TemplateListItem
import qa_engine
from qa_engine import ModuleType, OperationSet, Operation, OperationSet, ModuleMeta
import wpf
import clr

clr.AddReference("System.Xml")
from System.Windows.Controls import UserControl, StackPanel, TextBox, Button, Label, CheckBox, TextBlock
from System.Windows import Window, Thickness, TextWrapping, FontWeight, FontStyles, Visibility
from System.Windows.Forms import FolderBrowserDialog, DialogResult

CONFIG_EXTENSION = ".opset".lower()

logger = script.get_logger()


def arg_type_to_control(name,
                        arg_type,
                        value=None,
                        default_value=None,
                        on_change=None):
    stack_panel = StackPanel()
    stack_panel.Margin = Thickness(0, 5, 0, 5)

    def change_event_listener(fn_get_value):

        def wrapper(sender, e):
            logger.debug("change event: {}".format(e))
            on_change(fn_get_value())

        return wrapper

    if arg_type == bool:
        cb = CheckBox()
        cb.Content = name
        if value is not None:
            cb.IsChecked = bool(value)
        elif default_value is not None:
            cb.IsChecked = bool(default_value)
        else:
            cb.IsChecked = False
        if on_change:
            cb.Click += change_event_listener(lambda: cb.IsChecked)
        stack_panel.Children.Add(cb)
    elif arg_type == int or arg_type == float or arg_type == str:

        lb_name = Label()
        lb_name.Content = name + ":"
        lb_name.Margin = Thickness(0, 0, 5, 0)
        lb_name.FontWeight = FontWeight.FromOpenTypeWeight(500)
        tb = TextBox()
        tb.Text = str(value or default_value or "")
        tb.MinWidth = 100
        if on_change:
            parser = lambda x: x
            if arg_type == int:
                parser = int
            elif arg_type == float:
                parser = float
            tb.TextChanged += change_event_listener(lambda: parser(tb.Text))

        stack_panel.Children.Add(lb_name)
        stack_panel.Children.Add(tb)

    elif isinstance(arg_type, list):
        lb_name = Label()
        lb_name.Content = name + ":"
        lb_name.Margin = Thickness(0, 0, 5, 0)
        lb_name.FontWeight = FontWeight.FromOpenTypeWeight(500)

        btn_select = Button()

        btn_select.Content = "Select from list"
        multiselect = False
        if isinstance(default_value, list):
            multiselect = True

        def btn_click(sender, e):
            items = []
            values = value or default_value or []
            for item in arg_type:
                items.append(TemplateListItem(item, checked=item in values))

            res = forms.SelectFromList.show(items,
                                            multiselect=multiselect,
                                            title="Select {}".format(name))
            if res:
                if not multiselect:
                    if isinstance(res, list):
                        if len(res) > 0:
                            res = res[0]
                        else:
                            res = None

                if on_change:
                    on_change(res)
                    new_stack_panel = arg_type_to_control(
                        name,
                        arg_type,
                        value=res,
                        default_value=default_value,
                        on_change=on_change)
                    # replace the stack panel in the parent and replace it with
                    # the new one in the same position to refresh the selected value
                    parent = stack_panel.Parent
                    idx = parent.Children.IndexOf(stack_panel)
                    parent.Children.Remove(stack_panel)
                    parent.Children.Insert(idx, new_stack_panel)

        btn_select.Click += btn_click

        stack_panel.Children.Add(lb_name)
        stack_panel.Children.Add(btn_select)
    else:
        raise TypeError("arg_type not supported: {}".format(arg_type))

    return stack_panel


def get_config_folder():
    root = filemgr.user_config_path
    cfg_path = path.join(root, "OperationSet")
    if not path.exists(cfg_path):
        os.makedirs(cfg_path)
    return cfg_path


def get_xaml_path(xaml_name):
    return path.join(filemgr.engine_path, "qa_ui", xaml_name)


class ConfigMgr(WPFWindow):
    __op_set_mgr = None
    cfg_path = None

    def __init__(self, config_path=None, default_config_name=None):
        super(ConfigMgr, self).__init__(get_xaml_path('ConfigManager.xaml'),
                                        set_owner=True)
        self.__settings_filename = "config_manager.json"
        self.settings = filemgr.load_config(self.__settings_filename)
        self.cfg_available_list = []
        # The folder path of the config files
        self.cfg_path = self.settings.get("config_folder", get_config_folder())
        # The name of the current config
        self.cfg_current = self.settings.get("config_name", None)

        self.load_folder(config_path or self.cfg_path)
        self.select_config(default_config_name or self.cfg_current,
                           alert_if_fail=False)

        # UserControl
        self.__op_set_mgr = None

        # Bind Event
        # Window
        self.Closing += self.config_manager_closing
        # ComboBox Event
        self.combo_config.SelectionChanged += self.combo_config_selection_changed

        # Bind Data Source
        self.combo_config.ItemsSource = self.cfg_available_list
        self.combo_config.SelectedItem = self.cfg_current
        self.combo_config_selection_changed(self.combo_config, None)

    def load_folder(self, folder_path):
        """
        Load the config folder. 
        Return True if success.
        """
        if not path.exists(folder_path):
            return False

        if not self.check_unsaved_changes():
            return True

        filenames = os.listdir(folder_path)
        self.cfg_available_list = []

        for filename in filenames:
            if path.isfile(path.join(folder_path, filename)):
                if filename.lower().endswith(CONFIG_EXTENSION):
                    self.cfg_available_list.append(
                        filename[:-len(CONFIG_EXTENSION)])

        # bind
        self.combo_config.ItemsSource = self.cfg_available_list

        if len(self.cfg_available_list) != 0:
            self.combo_config.SelectedItem = self.cfg_available_list[0]
        else:
            self.combo_config.SelectedItem = None

        # refresh combo
        self.refresh_config_list()

        # save to settings
        self.settings["config_folder"] = folder_path

        return True

    def refresh_config_list(self):
        self.combo_config.ItemsSource = self.cfg_available_list
        self.combo_config.Items.Refresh()

    def select_config(self, cfg_name, alert_if_fail=True):
        """
         Select a config and then save the choice to settings.
         Return True if success.
        """
        if cfg_name not in self.cfg_available_list:
            if alert_if_fail:
                self.IsEnabled = False
                forms.alert("Config not be found: '{}'".format(cfg_name))
                self.IsEnabled = True
            return False
        self.cfg_current = cfg_name

        # save to settings
        self.settings["config_name"] = cfg_name

        return True

    def has_valid_config(self):
        return self.cfg_current in self.cfg_available_list

    def btn_rename_click(self, sender, e):
        if not self.has_valid_config():
            return

        # Make sure there are no unsaved changes
        if not self.check_unsaved_changes():
            return

        # Ask for new name
        new_name = forms.ask_for_string(
            default=self.cfg_current,
            title="Rename Config",
            prompt="Please enter a new name",
        )
        if new_name is not None and new_name != self.cfg_current:
            try:
                os.rename(
                    path.join(self.cfg_path,
                              self.cfg_current + CONFIG_EXTENSION),
                    path.join(self.cfg_path, new_name + CONFIG_EXTENSION))
                self.cfg_available_list.remove(self.cfg_current)
                self.cfg_available_list.append(new_name)
                self.cfg_available_list.sort()
                self.refresh_config_list()
                self.combo_config.SelectedItem = new_name
            except:
                self.IsEnabled = False
                forms.alert("Failed to rename config: {}".format(
                    self.cfg_current))
                self.IsEnabled = True

    def btn_delete_click(self, sender, e):

        if not self.has_valid_config():
            return

        # double ask
        self.IsEnabled = False
        res = forms.alert(
            "Do you want to delete this config \"{cfg}\"?".format(
                cfg=self.cfg_current),
            title="Delete",
            ok=False,
            yes=True,
            no=True)
        self.IsEnabled = True

        if res:
            try:
                os.remove(
                    path.join(self.cfg_path,
                              self.cfg_current + CONFIG_EXTENSION))
                self.cfg_available_list.remove(self.cfg_current)
                self.refresh_config_list()
                self.combo_config.SelectedItem = None
            except:
                self.IsEnabled = False
                forms.alert("Failed to delete config: {}".format(
                    self.cfg_current))
                self.IsEnabled = True

    def btn_select_folder_click(self, sender, e):

        folder = FolderBrowserDialog()
        folder.SelectedPath = self.cfg_path or ""
        folder.Description = "Select Config Folder"
        folder.ShowNewFolderButton = True
        result = folder.ShowDialog()
        filename = folder.SelectedPath
        if result == DialogResult.OK and filename:
            if not self.load_folder(filename):
                self.IsEnabled = False
                forms.alert("Failed to load config folder:\n{}".format(folder))
                self.IsEnabled = True

    def btn_open_folder_click(self, sender, e):
        script.show_folder_in_explorer(self.cfg_path)

    def check_unsaved_changes(self):
        """
        Check if there are unsaved changes. If true, pop up a window to ask if the user want to save the changes.
        Return true if the process should continue.
        """
        if self.__op_set_mgr and self.__op_set_mgr.unsaved_changes:
            self.IsEnabled = False
            res = forms.alert(
                "There are unsaved changes. Do you want to save them?",
                title="Unsaved Changes",
                options=["Save", "Discard", "Cancel"])
            self.IsEnabled = True
            if res == "Save":
                self.__op_set_mgr.save_to_file()
            elif res == "Cancel":
                return False
        return True

    def btn_create_click(self, sender, e):

        # Make sure there are no unsaved changes
        if not self.check_unsaved_changes():
            return

        # Find a new name
        i = 0

        def get_op_set_name(i):
            return "New Operation Set{}".format((" " +
                                                 str(i)) if i > 1 else "")

        while get_op_set_name(i) in self.cfg_available_list:
            i += 1
        op_set_name = get_op_set_name(i)
        filename = op_set_name + CONFIG_EXTENSION
        operation_set = OperationSet(name=op_set_name,
                                     description="",
                                     operations=[])
        filemgr.save_config(operation_set, path.join(self.cfg_path, filename))
        self.cfg_available_list.append(op_set_name)
        self.combo_config.SelectedItem = op_set_name

    def combo_config_selection_changed(self, sender, e):
        self.refresh_config_list()
        self.cfg_current = self.combo_config.SelectedItem

        if not self.has_valid_config():
            self.control_operation_set.Content = None
            return

        self.settings["config_name"] = self.cfg_current
        try:
            self.__op_set_mgr = OperationSetSettings.from_file(
                path.join(self.cfg_path, self.cfg_current + CONFIG_EXTENSION))

            self.control_operation_set.Content = self.__op_set_mgr
        except Exception as e:
            logger.error(e)
            self.IsEnabled = False
            forms.alert(
                "Failed to load config: {}".format(self.cfg_current),
                title="QA Extension Error",
                sub_msg=
                'Failed to load config: "{}". Please expend or check the log file for more information.'
                .format(self.cfg_current),
                expanded="\n".join(
                    traceback.format_exception(type(e), e, tb=None)),
            )
            self.IsEnabled = True

    def config_manager_closing(self, sender, e):
        if not self.check_unsaved_changes():
            e.Cancel = True
            return
        filemgr.save_config(self.settings, self.__settings_filename)


class OperationSetSettings(UserControl):
    """Config Manager Window"""
    op_set = None # type: OperationSet

    def __init__(self, op_set, save_path):
        # type: (OperationSet, str) -> None
        os.chdir(path.join(filemgr.engine_path, "qa_ui"))
        wpf.LoadComponent(self, get_xaml_path('OperationSetSettings.xaml'))
        self.init_op_set = copy.deepcopy(op_set)
        # type: OperationSet
        self.op_set = copy.deepcopy(op_set)
        # type: OperationSet
        self.save_path = save_path
        self.unsaved_changes = False
        self.__available_analyzers = qa_engine.get_available_modules(
            ModuleType.ANALYZER)
        self.__available_collectors = qa_engine.get_available_modules(
            ModuleType.COLLECTOR)
        self.__available_scope_selectors = qa_engine.get_available_modules(
            ModuleType.SCOPE_SELECTOR)
        self.__selected_op_index = None
        self.__window = Window.GetWindow(self)
        self.combo_scope_selector.ItemsSource = self.__get_module_metadata_list(
            self.__available_scope_selectors, ModuleType.SCOPE_SELECTOR)
        self.combo_collector.ItemsSource = self.__get_module_metadata_list(
            self.__available_collectors, ModuleType.COLLECTOR)
        self.combo_analyzer.ItemsSource = self.__get_module_metadata_list(
            self.__available_analyzers, ModuleType.ANALYZER)

        if len(self.__available_analyzers) == 0 or len(
                self.__available_collectors) == 0 or len(
                    self.__available_scope_selectors) == 0:
            self.IsEnabled = False
            forms.alert(
                "No analyzer or collector found. QA extension will not work!",
                title="QA Extension",
                exitscript=True)
            self.window.Close()

        # Event
        # ComboBox
        self.combo_collector.SelectionChanged += self.combo_collector_selection_changed
        self.combo_analyzer.SelectionChanged += self.combo_analyzer_selection_changed
        self.combo_scope_selector.SelectionChanged += self.combo_scope_selector_selection_changed

        # TextBox
        self.tb_cfg_desc.TextChanged += self.tb_cfg_desc_text_changed

        # TreeView
        self.treeview_operation.SelectionChanged += self.treeview_operation_selection_changed

        # Bind Data Source
        self.tb_cfg_desc.Text = self.op_set.description
        # TreeView
        self.treeview_operation.ItemsSource = self.op_set.operations

    @staticmethod
    def from_file(file_path):
        try:
            config = filemgr.load_config(file_path)
            return OperationSetSettings(
                filemgr.JsonParser.to_operation_set(config), file_path)
        except Exception as e:
            logger.error(e)
            forms.alert(
                "Failed to load config from file: {}".format(file_path),
                title="QA Extension Error",
                sub_msg=
                'Failed to load config from file: "{}". Please expend or check the log file for more information.'
                .format(file_path),
                expanded="\n".join(
                    traceback.format_exception(type(e), e, tb=None)),
            )
            return None

    def check_op_set(self):
        """
        Check the correctness of the config and return True if it is correct
        Pop up a warning window if it is not correct
        """
        return True
        # TODO: Do Some Check

    def save_to_file(self):
        """
        Save it to file
        """

        if self.save_path:
            # Match config name with filename
            if path.basename(
                    self.save_path) != self.op_set.name + CONFIG_EXTENSION:
                self.op_set.name = path.basename(self.save_path)[:-len(
                    CONFIG_EXTENSION)]
            
            filemgr.save_config(self.op_set, self.save_path)
            self.unsaved_changes = False
            self.refresh_operation_list()
        else:
            logger.error("save_path is None")

    def __get_module_metadata_list(self, module_names, module_type):
        """
        Get the metadata of the modules in the list
        """
        result = []
        for module_name in module_names:
            meta = self.__get_metadata(module_name, module_type)
            result.append(meta)
        result.sort(key=lambda x: x[ModuleMeta.NAME])
        return result

    @property
    def selected_op_index(self):
        return self.__selected_op_index

    @selected_op_index.setter
    def selected_op_index(self, value):
        try:
            if value == self.__selected_op_index:
                return
            if value < 0 or value >= len(self.op_set.operations):
                value = None
            self.__selected_op_index = value
            if value is None:
                self.combo_collector.IsEnabled = False
                self.combo_analyzer.IsEnabled = False
                self.combo_scope_selector.IsEnabled = False
                self.combo_collector.SelectedItem = None
                self.combo_analyzer.SelectedItem = None
                self.combo_scope_selector.SelectedItem = None
                self.update_advance_button(ModuleType.COLLECTOR)
                self.update_advance_button(ModuleType.ANALYZER)
                self.update_advance_button(ModuleType.SCOPE_SELECTOR)
            else:
                op = self.op_set.operations[value] # type: Operation|None

                collector_module_names = set(self.__available_collectors)
                analyzer_module_names = set(self.__available_analyzers)
                scope_selector_module_names = set(
                    self.__available_scope_selectors)
                
                collector_module_names.add(op.collector.module_name)
                analyzer_module_names.add(op.analyzer.module_name)
                scope_selector_module_names.add(op.scope_selector.module_name)

                
                meta_collectors = self.__get_module_metadata_list(
                    collector_module_names, ModuleType.COLLECTOR)
                meta_analyzers = self.__get_module_metadata_list(
                    analyzer_module_names, ModuleType.ANALYZER)
                meta_scope_selectors = self.__get_module_metadata_list(
                    scope_selector_module_names, ModuleType.SCOPE_SELECTOR)

                self.combo_collector.ItemsSource = meta_collectors
                self.combo_analyzer.ItemsSource = meta_analyzers
                self.combo_scope_selector.ItemsSource = meta_scope_selectors

                # Force Refresh Panel Content
                self.combo_collector.SelectedItem = None
                self.combo_analyzer.SelectedItem = None
                self.combo_scope_selector.SelectedItem = None

                self.combo_collector.SelectedItem = filter(
                    lambda x: x[ModuleMeta.MODULE_NAME] == op.collector.module_name, 
                    meta_collectors)[0]
                self.combo_analyzer.SelectedItem = filter(
                    lambda x: x[ModuleMeta.MODULE_NAME] == op.analyzer.module_name,
                    meta_analyzers)[0]
                self.combo_scope_selector.SelectedItem = filter(
                    lambda x: x[ModuleMeta.MODULE_NAME] == op.scope_selector.module_name, 
                    meta_scope_selectors)[0]

                self.combo_collector.IsEnabled = True
                self.combo_analyzer.IsEnabled = True
                self.combo_scope_selector.IsEnabled = True
                self.treeview_operation.SelectedItem = op
        except Exception as e:
            self.selected_op_index = None
            logger.error(e)
            logger.error(traceback.format_exc())
            forms.alert(
                "Failed to select operation: {}".format(value),
                title="QA Extension Error",
                sub_msg=
                'Failed to select operation: "{}". Please expend or check the log file for more information.'
                .format(value),
                expanded="\n".join(
                    traceback.format_exception(type(e), e, tb=None)),
            )
    def arg_change_event_factory(self,
                                 op_idx,
                                 module_type,
                                 arg_name,
                                 default_value=None):

        def arg_change(value):
            if module_type == ModuleType.COLLECTOR:
                self.op_set.operations[op_idx].collector_kwargs[
                    arg_name] = value
            elif module_type == ModuleType.ANALYZER:
                self.op_set.operations[op_idx].analyzer_kwargs[
                    arg_name] = value
            elif module_type == ModuleType.SCOPE_SELECTOR:
                self.op_set.operations[op_idx].scope_selector_kwargs[
                    arg_name] = value
            else:
                raise ValueError(
                    "module_type not supported: {}".format(module_type))
            if value != default_value:
                self.unsaved_changes = True

        return arg_change

    def __get_advance_button(self, module_type):
        if module_type == ModuleType.COLLECTOR:
            btn = self.btn_advance_collector
        elif module_type == ModuleType.ANALYZER:
            btn = self.btn_advance_analyzer
        elif module_type == ModuleType.SCOPE_SELECTOR:
            btn = self.btn_advance_scope_selector
        else:
            raise ValueError(
                "module_type not supported: {}".format(module_type))
        return btn

    def update_advance_button(self, module_type):
        btn = self.__get_advance_button(module_type)

        if self.selected_op_index is None or self.selected_op_index < 0 or self.selected_op_index >= len(
                self.op_set.operations):
            btn.Visibility = Visibility.Collapsed
            btn.IsEnabled = False
            return

        op = self.op_set.operations[self.selected_op_index]

        if module_type == ModuleType.COLLECTOR:
            arg_types = op.collector.get_arg_types()
        elif module_type == ModuleType.ANALYZER:
            arg_types = op.analyzer.get_arg_types()
        elif module_type == ModuleType.SCOPE_SELECTOR:
            arg_types = op.scope_selector.get_arg_types()

        if arg_types is None or len(arg_types) == 0:
            btn.Visibility = Visibility.Collapsed
            btn.IsEnabled = False
        else:
            btn.Visibility = Visibility.Visible
            btn.IsEnabled = True

    def refresh_operation_list(self):
        self.treeview_operation.ItemsSource = self.op_set.operations
        self.treeview_operation.Items.Refresh()

    @property
    def window(self):
        if not self.__window:
            self.__window = Window.GetWindow(self)
        return self.__window

    def btn_apply_click(self, sender, e):
        if self.check_op_set():
            self.DialogResult = True
            self.save_to_file()

    def btn_cancel_click(self, sender, e):
        self.DialogResult = False
        self.window.Close()

    def btn_reset_click(self, sender, e):
        self.IsEnabled = False
        res = forms.alert(
            "Do you want to reset this operation or the whole config?",
            title="Reset",
            options=[
                "Only reset this operation", "Reset the whole config", "Cancel"
            ])
        self.IsEnabled = True
        if res == "Only reset this operation":
            raise NotImplementedError()
        elif res == "Reset the whole config":
            raise NotImplementedError()
        self.op_set = self.init_op_set.copy()
        self.DialogResult = False

    def btn_tree_add_click(self, sender, e):
        try:
            operation = Operation(
                name="New Operation",
                scope_selector=self.__available_scope_selectors[0],
                collector=self.__available_collectors[0],
                analyzer=self.__available_analyzers[0],
            )
            if self.selected_op_index is not None:
                new_idx = self.selected_op_index + 1
                self.op_set.operations.insert(new_idx, operation)
            else:
                self.op_set.operations.append(operation)
                new_idx = len(self.op_set.operations) - 1
            self.unsaved_changes = True
            self.selected_op_index = new_idx
            self.refresh_operation_list()
        except Exception as e:
            logger.error(e)
            logger.error(traceback.format_exc())

    def btn_tree_del_click(self, sender, e):
        current_operation = sender.Tag
        current_operation_index = self.op_set.operations.index(
            current_operation)

        self.op_set.operations.pop(current_operation_index)
        self.unsaved_changes = True
        self.refresh_operation_list()

    def btn_tree_rename_click(self, sender, e):
        current_operation = sender.Tag
        current_operation_index = self.op_set.operations.index(
            current_operation)
        new_name = forms.ask_for_string(
            default=current_operation.name,
            title="Rename",
            prompt="Please enter a new name",
        )
        if new_name is not None and new_name != current_operation.name:
            current_operation.name = new_name
            self.unsaved_changes = True
            self.refresh_operation_list()

    def btn_tree_move_up_click(self, sender, e):
        current_operation = sender.Tag
        current_operation_index = self.op_set.operations.index(
            current_operation)

        if current_operation_index <= 0:
            # already at the top
            return

        self.op_set.operations.pop(current_operation_index)
        self.op_set.operations.insert(current_operation_index - 1,
                                      current_operation)
        self.selected_op_index = current_operation_index - 1
        self.refresh_operation_list()

    def btn_tree_move_down_click(self, sender, e):
        current_operation = sender.Tag
        current_operation_index = self.op_set.operations.index(
            current_operation)

        if current_operation_index >= len(self.op_set.operations) - 1:
            # already at the bottom
            return

        self.op_set.operations.pop(current_operation_index)
        self.op_set.operations.insert(current_operation_index + 1,
                                      current_operation)
        self.selected_op_index = current_operation_index + 1
        self.refresh_operation_list()

    def btn_advance_collector_click(self, sender, e):
        try:
            operation = self.op_set.operations[self.selected_op_index]
            args = operation.collector.get_default_args()
            args.update(operation.collector_kwargs)
            result = operation.collector.show_additional_settings(
                arg_values=args, )
            if result:
                operation.collector_kwargs = result
                self.refresh_operation_list()
                self.tb_desc_collector.Text = self.op_set.operations[
                    self.selected_op_index].collector.get_description(**result)
        except Exception as e:
            logger.error(e)
            logger.error(traceback.format_exc())

    def btn_advance_analyzer_click(self, sender, e):
        try:
            operation = self.op_set.operations[self.selected_op_index]
            args = operation.analyzer.get_default_args()
            args.update(operation.analyzer_kwargs)
            result = operation.analyzer.show_additional_settings(
                arg_values=args)
            if result:
                operation.analyzer_kwargs = result
                self.refresh_operation_list()
                self.tb_desc_analyzer.Text = self.op_set.operations[
                    self.selected_op_index].analyzer.get_description(**result)
        except Exception as e:
            logger.error(e)
            # trace
            logger.error(traceback.format_exc())

    def btn_advance_scope_selector_click(self, sender, e):
        try:
            operation = self.op_set.operations[self.selected_op_index]
            args = operation.scope_selector.get_default_args()
            args.update(operation.scope_selector_kwargs)
            result = operation.scope_selector.show_additional_settings(
                arg_values=args)
            if result:
                operation.scope_selector_kwargs = result
                self.refresh_operation_list()
                self.tb_desc_scope_selector.Text = self.op_set.operations[
                    self.selected_op_index].scope_selector.get_description(
                        **result)
        except Exception as e:
            logger.error(e)
            logger.error(traceback.format_exc())

    def tb_cfg_desc_text_changed(self, sender, e):
        if self.op_set.description == self.tb_cfg_desc.Text:
            return
        self.op_set.description = self.tb_cfg_desc.Text
        self.unsaved_changes = True

    def combo_collector_selection_changed(self, sender, e):
        if self.selected_op_index is None or self.combo_collector.SelectedItem is None:
            return

        collector_name = self.combo_collector.SelectedItem[
            ModuleMeta.MODULE_NAME]
        if collector_name not in self.__available_collectors:
            return
        op = self.op_set.operations[self.selected_op_index]
        collector = qa_engine.get_collector(collector_name)

        op.collector = collector
        self.update_advance_button(ModuleType.COLLECTOR)
        self.refresh_operation_list()

        self.tb_desc_collector.Text = collector.get_description(
            **op.collector_kwargs)

    def combo_analyzer_selection_changed(self, sender, e):
        if self.selected_op_index is None or self.combo_analyzer.SelectedItem is None:
            return
        analyzer_name = self.combo_analyzer.SelectedItem[
            ModuleMeta.MODULE_NAME]
        if analyzer_name not in self.__available_analyzers:
            return

        op = self.op_set.operations[self.selected_op_index]
        op.analyzer = qa_engine.get_analyzer(analyzer_name)
        self.update_advance_button(ModuleType.ANALYZER)
        self.refresh_operation_list()
        self.tb_desc_analyzer.Text = op.analyzer.get_description(
            **op.analyzer_kwargs)

    def combo_scope_selector_selection_changed(self, sender, e):

        if self.selected_op_index is None or self.combo_scope_selector.SelectedItem is None:
            return
        scope_selector_name = self.combo_scope_selector.SelectedItem[
            ModuleMeta.MODULE_NAME]
        if scope_selector_name not in self.__available_scope_selectors:
            return

        op = self.op_set.operations[self.selected_op_index]
        op.scope_selector = qa_engine.get_scope_selector(scope_selector_name)
        self.update_advance_button(ModuleType.SCOPE_SELECTOR)
        self.refresh_operation_list()
        self.tb_desc_scope_selector.Text = op.scope_selector.get_description(
            **op.scope_selector_kwargs)

    def treeview_operation_selection_changed(self, sender, e):
        if self.treeview_operation.SelectedIndex < 0:
            self.selected_op_index = None
        else:
            self.selected_op_index = self.treeview_operation.SelectedIndex

    def __get_metadata(self, module_name, module_type):
        """
        Get the metadata of the module
        """
        module = qa_engine.get_module(module_name, module_type)
        return module.metadata


class OperationSettings(WPFWindow):
    """Config Manager Window"""

    def __init__(self, arg_values, metadata):
        os.chdir(path.join(filemgr.engine_path, "qa_ui"))
        wpf.LoadComponent(self, get_xaml_path('OperationSettings.xaml'))
        self.unsaved_changes = False
        self.__metadata = metadata
        self.__arg_types = metadata[ModuleMeta.ARG_TYPES]
        self.__arg_values = arg_values
        self.__default_args = metadata[ModuleMeta.DEFAULT_ARGS]
        self.generate_operation_panel()
        self.Closing += self.closing

    def get_arg_values(self):
        return self.__arg_values

    @property
    def result(self):
        return self.__arg_values

    def show(self):
        """
        Show the window and return the result as dictionary
        """
        return self.ShowDialog()

    def arg_change_event_factory(self, arg_name, default_value=None):

        def arg_change(value):
            if value != default_value:
                self.__arg_values[arg_name] = value
                self.unsaved_changes = True

        return arg_change

    def clear_operation_panel(self):
        panel = self.ctrl_panel
        panel.Content = None

    @staticmethod
    def new_textblock(text, bold=False, fontsize=12):
        tb = TextBlock()
        tb.TextWrapping = TextWrapping.WrapWithOverflow
        tb.Text = text
        tb.FontSize = fontsize
        if bold:
            tb.FontWeight = FontWeight.FromOpenTypeWeight(700)
        return tb

    def generate_operation_panel(self):
        stack_panel = StackPanel()
        metadata = self.__metadata
        if metadata[ModuleMeta.NAME]:
            tb = self.new_textblock(metadata[ModuleMeta.NAME], bold=True)
            tb.Margin = Thickness(0, 5, 0, 5)
            tb.FontSize += 2
            stack_panel.Children.Add(tb)

        if metadata[ModuleMeta.DESCRIPTION]:
            tb = self.new_textblock(metadata[ModuleMeta.DESCRIPTION])
            stack_panel.Children.Add(tb)

        if metadata[ModuleMeta.RETURN]:
            tb = self.new_textblock(" (Return: {})".format(
                metadata[ModuleMeta.RETURN]))
            # italic
            tb.FontStyle = FontStyles.Italic
            stack_panel.Children.Add(tb)

        container = self.ctrl_panel

        for arg_name, arg_type in self.__arg_types.items():
            stack_panel.Children.Add(
                arg_type_to_control(
                    arg_name,
                    arg_type=arg_type,
                    value=self.__arg_values.get(arg_name, None),
                    default_value=self.__default_args.get(arg_name, None),
                    on_change=self.arg_change_event_factory(
                        arg_name,
                        default_value=self.__default_args.get(arg_name,
                                                              None))))

        if len(stack_panel.Children) == 0:
            lb = Label()
            lb.Content = "\n[No Arguments Available]"
            stack_panel.Children.Add(lb)
        container.Content = stack_panel

    def btn_ok_click(self, sender, e):
        self.DialogResult = True
        self.Close()

    def btn_cancel_click(self, sender, e):
        self.DialogResult = False
        self.Close()

    def closing(self, sender, e):
        if not self.check_unsaved_changes():
            e.Cancel = True
            return

    def check_unsaved_changes(self):
        """
        Check if there are unsaved changes. If true, pop up a window to ask if the user want to save the changes.
        Return true if the process should continue.
        """
        if self.unsaved_changes and not self.DialogResult:
            self.IsEnabled = False
            res = forms.alert(
                "There are unsaved changes. Do you want to save them?",
                title="Unsaved Changes",
                options=["Save", "Discard", "Cancel"])
            self.IsEnabled = True
            if res == "Save":
                self.DialogResult = True
            elif res == "Cancel":
                self.DialogResult = False
        return True
