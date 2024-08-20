from pyrevit import script, forms
from pyrevit import revit, DB, UI
from pyrevit import HOST_APP, EXEC_PARAMS
import Autodesk.Revit.DB as db
import qa_engine
import filemgr
from qa_report import print_reports
import clr

clr.AddReference('PresentationCore')
clr.AddReference('PresentationFramework')
clr.AddReference('System.Windows.Forms')
#clr.AddReference('IronPython.Wpf')
import sys
import re



from System.Windows.Controls import ComboBox, ComboBoxItem  # Import ComboBoxItem

xamlfile_family_selection = script.get_bundle_file('SelectMEPFamilyType.xaml')

xamlfile_parameter_pairs_selection = script.get_bundle_file('SelectParams.xaml')

import wpf
from System import Windows


family_instance_parameters = []
family_instance_parameters_names = []
params_names_vs_params_objs_dict = {}
family_instances_of_selected_family = []

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
            # print(self.selected_value)
        else:
            print("No Item Selected")




class ParameterPairsSelectionWindow(Windows.Window):

    def __init__(self, selected_value):
        wpf.LoadComponent(self, xamlfile_parameter_pairs_selection)

        self.selected_value = selected_value

        self.selected_family_instances_list = []

        self.selected_value_space_1 = None
        self.selected_value_MEP_Instance_1 = None

        self.selected_value_space_2 = None
        self.selected_value_MEP_Instance_2 = None

        self.selected_value_space_3 = None
        self.selected_value_MEP_Instance_3 = None

        self.selected_value_space_4 = None
        self.selected_value_MEP_Instance_4 = None

        self.should_divide_by_number_MEP_elements_in_space = False

        MEP_family_name = self.selected_value
        # Collect all Families in the Document
        family_collector = DB.FilteredElementCollector(doc).OfClass(DB.Family)
        # Collect all Spaces and Rooms in the Active View
        spaces_collector = DB.FilteredElementCollector(doc, doc.ActiveView.Id).OfClass(DB.SpatialElement)

        # # DeBugging (commented)
        # for f in family_collector:
        #     print("Family_Name: ".format(f.Name))
        # print("Family Collector", list(family_collector.ToElements()))

        # Collect only Families which were selected from Combo Box in the First Popup Window
        MEP_families = [f for f in family_collector if f.Name == MEP_family_name]

        # Transform Filtered Collector to Elements
        spatial_elements = spaces_collector.ToElements()
       

        # # DeBugging (commented)
        # for spatial_family in spatial_elements:
        #     print("Spatial Element Type {}".format(spatial_family.SpatialElementType))

        # separate Spaces from Rooms
        self.spaces_elements = [spatial_elem for spatial_elem in spatial_elements if spatial_elem.SpatialElementType == DB.SpatialElementType.Space]
        print("So many spaces: {}".format(len(self.spaces_elements)))

        # populate Combo Boxes for Spaces
        if self.spaces_elements:
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
        else:
            print("No spaces elements. Something went wrong. EXIT PROGRAM")
            sys.exit()
            self.Close()


        if MEP_families:
            for MEP_family in MEP_families:
                # Get the ElementId of the selected family
                family_ids = list(MEP_family.GetFamilySymbolIds())

                # # DeBugging (commented)
                # print(type(family_ids))
                # print(family_ids)

                

                # Define the filter for FamilyInstances of the selected family
                for family_id in family_ids:

                    # setup family instance filter, it uses FamilySymbolIds
                    family_instance_filter = DB.FamilyInstanceFilter(doc, family_id)

                    # Get all family instances of the selected family
                    family_instance_collector = DB.FilteredElementCollector(doc, doc.ActiveView.Id).WherePasses(family_instance_filter)
                    mep_family_Instances = family_instance_collector.ToElements()

                    self.selected_family_instances_list += mep_family_Instances

                    # family_instances_of_selected_family += mep_family_Instances

                    # print("Len Family Instancies MEP: {}".format(len(mep_family_Instances)))

                    for family_instance in mep_family_Instances:
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
                for my_family_instance in mep_family_Instances:
                    # Do something with each family instance
                    pass
        else:
            print("Family {} not found.".format(MEP_family_name))

        

    def transfer_parameters(self, space_elem, MEP_instance, space_parameter_name, MEP_instance_parameter_name, number_MEP_elems_in_space):

        if space_parameter_name is not None and MEP_instance_parameter_name is not None:

            space_parameter = space_elem.LookupParameter(space_parameter_name)
            MEP_parameter = MEP_instance.LookupParameter(MEP_instance_parameter_name)

            if (MEP_parameter is not None) and (space_parameter is not None):

                if number_MEP_elems_in_space > 1 and self.should_divide_by_number_MEP_elements_in_space:
                    divided_space_parameter_as_value_string = self.divide_by_MEP_elements_number_if_possible(parameter_as_value_string=space_parameter.AsValueString(), MEP_elem_number_in_space=number_MEP_elems_in_space)
                    MEP_parameter.Set(divided_space_parameter_as_value_string)
                else:
                # print("Transaction fire up: MEP instance param: {}; space param: {}".format(MEP_instance_parameter_name, space_parameter_name))
                    MEP_parameter.Set(space_parameter.AsValueString())
                
                #print("Transaction committed")
            else:
                pass
                #print("MEP and/or space parameter do not exist")
        else:
            pass
            #print("Parameter not filled")



    def btn_ok_clicked(self, sender, e):

        counter_matches = 0

        t = DB.Transaction(doc, "Param transfer CUSTOM")
        t.Start()

        closed = False

        print("In Progress ... ")





        try: 
            

            for space_elem in self.spaces_elements:

                MEP_elem_number_in_space = 0

                list_MEP_instances_in_space = []

                for MEP_instance in self.selected_family_instances_list:
                    phase = list(doc.Phases)[-1]  # retrieve the last phase of the project
                    # print("MEP Instance Space type: {}".format(type(MEP_instance.Space[phase])))
                    
                    # if MEP_instance.Space[phase] is not None:
                    #     mep_location_space_id = MEP_instance.Space[phase].Id
                    # else:
                    #     mep_location_space_id = MEP_instance.Space.Id
                    mep_location_point = MEP_instance.Location.Point
                    #print("SPACE: ", space_elem)
                    if space_elem.IsPointInSpace(mep_location_point):
                        list_MEP_instances_in_space.append(MEP_instance)
                        MEP_elem_number_in_space += 1


                for MEP_instance in list_MEP_instances_in_space:
                    
                    phase = list(doc.Phases)[-1]  # retrieve the last phase of the project
                    # print("MEP Instance Space type: {}".format(type(MEP_instance.Space[phase])))
                    
                    # if MEP_instance.Space[phase] is not None:
                    #     mep_location_space_id = MEP_instance.Space[phase].Id
                    # else:
                    #     mep_location_space_id = MEP_instance.Space.Id
                    mep_location_point = MEP_instance.Location.Point
                    #print("SPACE: ", space_elem)
                  

                    counter_matches += 1

                    self.transfer_parameters(space_elem=space_elem, MEP_instance=MEP_instance,
                                            space_parameter_name=self.selected_value_space_1, 
                                            MEP_instance_parameter_name=self.selected_value_MEP_Instance_1, number_MEP_elems_in_space=MEP_elem_number_in_space)
                    
                    self.transfer_parameters(space_elem=space_elem, MEP_instance=MEP_instance,
                                            space_parameter_name=self.selected_value_space_2, 
                                            MEP_instance_parameter_name=self.selected_value_MEP_Instance_2, number_MEP_elems_in_space=MEP_elem_number_in_space)
                    
                    self.transfer_parameters(space_elem=space_elem, MEP_instance=MEP_instance,
                                            space_parameter_name=self.selected_value_space_3, 
                                            MEP_instance_parameter_name=self.selected_value_MEP_Instance_3, number_MEP_elems_in_space=MEP_elem_number_in_space)
                    
                    self.transfer_parameters(space_elem=space_elem, MEP_instance=MEP_instance,
                                            space_parameter_name=self.selected_value_space_4, 
                                            MEP_instance_parameter_name=self.selected_value_MEP_Instance_4, number_MEP_elems_in_space=MEP_elem_number_in_space)
        

        except Exception as error:
            print("ERROR: ", error)
            t.Commit()
            self.Close()
            closed = True
                    # print("Match")
        if not closed:
            t.Commit()
            self.Close()

        print("Work done successfully!")
                    
        print("Number of changed instances: {}". format(counter_matches))
        
        
        self.Close()

    
    def combobox_item_spaces_1_SelectionChanged(self, sender, e):
        selected_item = self.combo_parameter_from_space_1.SelectedItem
        if selected_item:
            self.selected_value_space_1 = selected_item.Content
            # print(self.selected_value)
        else:
            print("No Item Selected")
    
    def combobox_item_spaces_2_SelectionChanged(self, sender, e):
        selected_item = self.combo_parameter_from_space_2.SelectedItem
        if selected_item:
            self.selected_value_space_2 = selected_item.Content
            # print(self.selected_value)
        else:
            print("No Item Selected")

    def combobox_item_spaces_3_SelectionChanged(self, sender, e):
        selected_item = self.combo_parameter_from_space_3.SelectedItem
        if selected_item:
            self.selected_value_space_3 = selected_item.Content
            # print(self.selected_value)
        else:
            print("No Item Selected")
    
    def combobox_item_spaces_4_SelectionChanged(self, sender, e):
        selected_item = self.combo_parameter_from_space_4.SelectedItem
        if selected_item:
            self.selected_value_space_4 = selected_item.Content
            # print(self.selected_value)
        else:
            print("No Item Selected")


    def combobox_item_MEP_1_SelectionChanged(self, sender, e):
        selected_item = self.combo_param_to_1.SelectedItem
        if selected_item:
            self.selected_value_MEP_Instance_1 = selected_item.Content
            # print(self.selected_value)
        else:
            print("No Item Selected")

    def combobox_item_MEP_2_SelectionChanged(self, sender, e):
        selected_item = self.combo_param_to_2.SelectedItem
        if selected_item:
            self.selected_value_MEP_Instance_2 = selected_item.Content
            # print(self.selected_value)
        else:
            print("No Item Selected")

    def combobox_item_MEP_3_SelectionChanged(self, sender, e):
        selected_item = self.combo_param_to_3.SelectedItem
        if selected_item:
            self.selected_value_MEP_Instance_3 = selected_item.Content
            # print(self.selected_value)
        else:
            print("No Item Selected")

    def combobox_item_MEP_4_SelectionChanged(self, sender, e):
        selected_item = self.combo_param_to_4.SelectedItem
        if selected_item:
            self.selected_value_MEP_Instance_4 = selected_item.Content
            # print(self.selected_value)
        else:
            print("No Item Selected")


    def handle_checked_division_by_MEP_elem_number(self, sender, e):

        self.should_divide_by_number_MEP_elements_in_space = True

        # print("self.should_divide_by_number_MEP_elements_in_space: ", self.should_divide_by_number_MEP_elements_in_space)
    
    def handle_unchecked_division_by_MEP_elem_number(self, sender, e):

        self.should_divide_by_number_MEP_elements_in_space = False

        # print("self.should_divide_by_number_MEP_elements_in_space: ", self.should_divide_by_number_MEP_elements_in_space)
    
    def divide_by_MEP_elements_number_if_possible(self, parameter_as_value_string, MEP_elem_number_in_space):

        re_pattern = r'\d+,\d+|\d+\.\d+|\d+'

        numbers = re.findall(pattern=re_pattern, string=parameter_as_value_string)

        print("Numbers recognized", numbers)

        last_number_position = re.search(pattern=re_pattern, string=parameter_as_value_string).end()

        string_part = parameter_as_value_string[last_number_position:]

        # if numbers is defined, take only the first [0]th element because of possible numbers in the unit names like m2
        # consider CheckBox' state
        if numbers is not None and self.should_divide_by_number_MEP_elements_in_space:
            number_part = numbers[0]
            # check if the string is a correct number
            if number_part.isnumeric():

                float_number_part = float(number_part)
                result_float_number_part = float_number_part / MEP_elem_number_in_space

                # concatenate new number and string part
                new_parameter_as_value_string = str(result_float_number_part) + string_part

                return new_parameter_as_value_string
            else:
                return parameter_as_value_string
        else:
            return parameter_as_value_string
        


        
            
        
        




    
    

        



# MyWindow().ShowDialog()

if __name__ == "__main__":
    doc = revit.doc
    uidoc = HOST_APP.uidoc
    filtered_collector = DB.FilteredElementCollector(doc)

    # all_MEPFamilyTypes = DB.FilteredElementCollector(doc, doc.ActiveView.Id).OfCategory(db.BuiltInCategory.OST_DuctAccessory).ToElements()

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

