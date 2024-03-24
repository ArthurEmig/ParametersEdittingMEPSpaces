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

xamlfile = script.get_bundle_file('SelectMEPFamilyType.xaml')

import wpf
from System import Windows

class MyWindow(Windows.Window):

    def __init__(self):
        wpf.LoadComponent(self, xamlfile)
        self.selected_value = None

    def btn_ok_clicked():
        pass

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

    my_window_obj = MyWindow()
    my_window_obj.populate_combo_box_family_types(doc)
    my_window_obj.ShowDialog()

    # MyWindow().ShowDialog()

    # print("all MEP: ", all_family_types)

