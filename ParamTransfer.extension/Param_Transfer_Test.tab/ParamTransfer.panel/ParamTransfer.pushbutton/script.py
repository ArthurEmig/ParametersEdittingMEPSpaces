from pyrevit import script, forms
from pyrevit import revit, DB, UI
from pyrevit import HOST_APP, EXEC_PARAMS
import Autodesk.Revit.DB as db
import qa_engine
import filemgr
from qa_report import print_reports
import clr
clr.AddReference('System.Windows.Forms')
clr.AddReference('IronPython.wpf')



from System.Windows.Controls import ComboBox, ComboBoxItem  # Import ComboBoxItem

xamlfile_family_selection = script.get_bundle_file('SelectMEPFamilyType.xaml')

xamlfile_parameter_pairs_selection = script.get_bundle_file('SelectParams.xaml')

import wpf
from System import Windows


family_instance_parameters = []
family_instance_parameters_names = []
params_names_vs_params_objs_dict = {}

def isMEPInstanceInSpace(MEPInstance_elem, space_elem):

    mep_instance_space_id = MEPInstance_elem.Space.Id
    space_id = space_elem.Id

    return mep_instance_space_id == space_id



class FamilySelectionWindow(Windows.Window):

    def __init__(self):
        wpf.LoadComponent(self, xamlfile_family_selection)
        self.selected_value = None

    def btn_ok_clicked(self, sender, e):
        self.Close()
        ParameterPairsSelectionWindow(self.selected_value).ShowDialog()

    def populate_combo_box_family_types(self, doc):
        all_MEP_family_types = filtered_collector.OfClass(db.FamilySymbol).ToElements()

        quantity_MEP_Elements = len(all_MEP_family_types)

        all_family_names = list(set([elem.Family.Name for elem in all_MEP_family_types]))

        for family_name in all_family_names:
            combobox_item = ComboBoxItem()
            combobox_item.Content = family_name
            self.combo_family_type.Items.Add(combobox_item)
        
    def comboBoxFamilyTypes_SelectionChanged(self, sender, e):
        selected_item = self.combo_family_type.SelectedItem
        if selected_item:
            self.selected_value = selected_item.Content
            print(self.selected_value)
        else:
            print("No Item Selected")




class ParameterPairsSelectionWindow(Windows.Window):

    def __init__(self, selected_value):
        wpf.LoadComponent(self, xamlfile_parameter_pairs_selection)

        self.selected_value = selected_value

        self.selected_value_space_1 = None
        self.selected_value_MEP_Instance_1 = None

        self.selected_value_space_2 = None
        self.selected_value_MEP_Instance_2 = None

        self.selected_value_space_3 = None
        self.selected_value_MEP_Instance_3 = None

        self.selected_value_space_4 = None
        self.selected_value_MEP_Instance_4 = None
        # Find the Family object corresponding to the "MyFamily" family
        MEP_family_name = self.selected_value # Replace "MyFamily" with the actual name of your family
        family_collector = DB.FilteredElementCollector(doc).OfClass(DB.Family)
        spaces_collector = DB.FilteredElementCollector(doc).OfClass(DB.SpatialElement)
        MEP_families = [f for f in family_collector if f.Name == MEP_family_name]
        spatial_elements = spaces_collector.ToElements()
       
        for spatial_family in spatial_elements:
            print("Spatial Element Type {}".format(spatial_family.SpatialElementType))
        self.spaces_elements = [spatial_elem for spatial_elem in spatial_elements if spatial_elem.SpatialElementType == DB.SpatialElementType.Space]
        print("So many spaces: {}".format(len(self.spaces_elements)))

        # populate Combo Boxes for Spaces
        self.spaces_params = list(self.spaces_elements[0].GetOrderedParameters())
        for space_param in self.spaces_params:
            space_param_name = space_param.Definition.Name
            combobox_item_spaces_1 = ComboBoxItem()
            combobox_item_spaces_2 = ComboBoxItem()
            combobox_item_spaces_3 = ComboBoxItem()
            combobox_item_spaces_4 = ComboBoxItem()
            combobox_item_spaces_1.Content = space_param_name
            combobox_item_spaces_2.Content = space_param_name
            combobox_item_spaces_3.Content = space_param_name
            combobox_item_spaces_4.Content = space_param_name
            self.combo_parameter_from_space_1.Items.Add(combobox_item_spaces_1)
            self.combo_parameter_from_space_2.Items.Add(combobox_item_spaces_2)
            self.combo_parameter_from_space_3.Items.Add(combobox_item_spaces_3)
            self.combo_parameter_from_space_4.Items.Add(combobox_item_spaces_4)


        

        

        if MEP_families:
            for MEP_family in MEP_families:
            # Get the ElementId of the "MyFamily" family
                family_ids = list(MEP_family.GetFamilySymbolIds())

                # print(type(family_ids))
                # print(family_ids)

                elem_symbol = doc.GetElement(family_ids[0])

                # print("Symbol: ", type(elem_symbol))
                family_instances_of_selected_family = []

                # Define the filter for FamilyInstances of the "MyFamily" family
                for family_id in family_ids:
                    family_instance_filter = DB.FamilyInstanceFilter(doc, family_id)

                    # Get all family instances of the "MyFamily" family
                    family_instance_collector = DB.FilteredElementCollector(doc).WherePasses(family_instance_filter)
                    my_family_instances = family_instance_collector.ToElements()

                    family_instances_of_selected_family += my_family_instances

                    for family_instance in my_family_instances:
                        for param in family_instance.Parameters:
                            if param not in family_instance_parameters:
                                param_name = param.Definition.Name


                                # Populate param names dictionary, to find each param on its Definition.Name
                                if param_name not in params_names_vs_params_objs_dict:
                                    params_names_vs_params_objs_dict[param_name] = [param]
                                else:
                                    temp_list_params = params_names_vs_params_objs_dict[param_name]
                                    temp_list_params.append(param)
                                    params_names_vs_params_objs_dict[param_name] = temp_list_params
                                

                                # Populate Combo Boxes
                                if param_name not in family_instance_parameters_names:
                                    family_instance_parameters_names.append(param_name)
                                    combobox_item_1 = ComboBoxItem()
                                    combobox_item_2 = ComboBoxItem()
                                    combobox_item_3 = ComboBoxItem()
                                    combobox_item_4 = ComboBoxItem()
                                    combobox_item_1.Content = param_name
                                    combobox_item_2.Content = param_name
                                    combobox_item_3.Content = param_name
                                    combobox_item_4.Content = param_name
                                    self.combo_param_to_1.Items.Add(combobox_item_1)
                                    self.combo_param_to_2.Items.Add(combobox_item_2)
                                    self.combo_param_to_3.Items.Add(combobox_item_3)
                                    self.combo_param_to_4.Items.Add(combobox_item_4)

                    # print("So many Instances of {}: {} ".format(family_id, len(my_family_instances)))

                # Now you can process the family instances as needed
                for my_family_instance in my_family_instances:
                    # Do something with each family instance
                    pass
        else:
            print("Family 'MyFamily' not found.")

        

    def btn_ok_clicked(self, sender, e):


        
        
        self.Close()

    
    def combobox_item_spaces_1_SelectionChanged(self, sender, e):
        selected_item = self.combo_parameter_from_space_1.SelectedItem
        if selected_item:
            self.selected_value_space_1 = selected_item.Content
            print(self.selected_value)
        else:
            print("No Item Selected")
    
    def combobox_item_spaces_2_SelectionChanged(self, sender, e):
        selected_item = self.combo_parameter_from_space_2.SelectedItem
        if selected_item:
            self.selected_value_space_2 = selected_item.Content
            print(self.selected_value)
        else:
            print("No Item Selected")

    def combobox_item_spaces_3_SelectionChanged(self, sender, e):
        selected_item = self.combo_parameter_from_space_3.SelectedItem
        if selected_item:
            self.selected_value_space_3 = selected_item.Content
            print(self.selected_value)
        else:
            print("No Item Selected")
    
    def combobox_item_spaces_4_SelectionChanged(self, sender, e):
        selected_item = self.combo_parameter_from_space_4.SelectedItem
        if selected_item:
            self.selected_value_space_4 = selected_item.Content
            print(self.selected_value)
        else:
            print("No Item Selected")


    def combobox_item_MEP_1_SelectionChanged(self, sender, e):
        selected_item = self.combo_param_to_1.SelectedItem
        if selected_item:
            self.selected_value_MEP_Instance_1 = selected_item.Content
            print(self.selected_value)
        else:
            print("No Item Selected")

    def combobox_item_MEP_2_SelectionChanged(self, sender, e):
        selected_item = self.combo_param_to_2.SelectedItem
        if selected_item:
            self.selected_value_MEP_Instance_2 = selected_item.Content
            print(self.selected_value)
        else:
            print("No Item Selected")

    def combobox_item_MEP_3_SelectionChanged(self, sender, e):
        selected_item = self.combo_param_to_3.SelectedItem
        if selected_item:
            self.selected_value_MEP_Instance_3 = selected_item.Content
            print(self.selected_value)
        else:
            print("No Item Selected")

    def combobox_item_MEP_4_SelectionChanged(self, sender, e):
        selected_item = self.combo_param_to_4.SelectedItem
        if selected_item:
            self.selected_value_MEP_Instance_4 = selected_item.Content
            print(self.selected_value)
        else:
            print("No Item Selected")
    
    

        



# MyWindow().ShowDialog()

if __name__ == "__main__":
    doc = revit.doc
    uidoc = HOST_APP.uidoc
    filtered_collector = DB.FilteredElementCollector(doc)

    # all_MEPFamilyTypes = DB.FilteredElementCollector(doc).OfCategory(db.BuiltInCategory.OST_DuctAccessory).ToElements()

    # all_MEP_family_types = filtered_collector.OfClass(db.FamilySymbol).ToElements()

    # quantity_MEP_Elements = len(all_MEP_family_types)

    # all_family_names = list(set([elem.Family.Name for elem in all_MEP_family_types]))

    # for family_name in all_family_names:
    #     combobox_item = ComboBoxItem()
    #     combobox_item.Content = family_name
    #     self.combo_family_type.Items.Add(combobox_item)

    # all_family_types = list(set([elem.GetTypeId() for elem in all_MEP_family_types]))

    my_window_obj = FamilySelectionWindow()
    my_window_obj.populate_combo_box_family_types(doc)
    my_window_obj.ShowDialog()

    # MyWindow().ShowDialog()

    # print("all MEP: ", all_family_types)

