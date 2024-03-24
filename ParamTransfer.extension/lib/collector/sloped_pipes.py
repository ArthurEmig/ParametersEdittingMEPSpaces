# coding: UTF-8
from qa_engine import Collector, get_collector
from pyrevit import HOST_APP, EXEC_PARAMS
from pyrevit import revit, DB, UI
from pyrevit import script
import Autodesk.Revit.DB as db
import math


NAME = 'Sloped pipes'
DESCRIPTION = 'Sloped pipes'
RETURN = 'list[Element]'
AUTHOR = 'Arthur Emig'

doc = revit.doc
uidoc = HOST_APP.uidoc
logger = script.get_logger()




class SlopedPipesCollector(Collector):
    name = NAME
    _author = AUTHOR

    def collect(self, scope=[], **kwargs):
        # STEP 4: Get all pipes in the view
        all_pipes = []
        for view in scope:
            all_pipes += list(db.FilteredElementCollector(doc, view.Id)\
                    .OfCategory(db.BuiltInCategory.OST_PipeCurves)\
                    .ToElements())
        print("✔")
        print("  ➜ Found {num} pipes in the currently active view.".format(num=len(all_pipes)))
        vertical_pipes = []
        weird_pipes = []
        sloped_pipes = []
        horizontal_pipes = []

        for pipe in all_pipes:
            pipe_type = is_vertical_weird_sloped_horizontal(pipe=pipe)
            if pipe_type == 'vertical':
                vertical_pipes.append(pipe)
            elif pipe_type == 'weird':
                weird_pipes.append(pipe)
            elif pipe_type == 'sloped':
                sloped_pipes.append(pipe)
            elif pipe_type == 'horizontal':
                horizontal_pipes.append(pipe)

        print("✔")
        print("  ➜ Found {num} vertical pipes in the currently active view.".format(num=len(vertical_pipes)))
        print("  ➜ Found {num} weird pipes in the currently active view.".format(num=len(weird_pipes)))
        print("  ➜ Found {num} sloped pipes in the currently active view.".format(num=len(sloped_pipes)))
        print("  ➜ Found {num} horizontal pipes in the currently active view.".format(num=len(horizontal_pipes)))

        return sloped_pipes

def get_points(pipe):
    """Get the start and end point of a pipe."""
    curve = pipe.Location.Curve
    point0 = curve.GetEndPoint(0)
    point1 = curve.GetEndPoint(1)
    return point0, point1

def is_vertical_weird_sloped_horizontal(pipe, vertical_tolerance = 1, weird_thr_upper = 65, sloped_thr_upper=90):
    """Check if a pipe is vertical (within the given angle tolerance)."""
    point1, point2 = get_points(pipe)
    dz = abs(point1.Z - point2.Z)
    if dz:  # is not horizontal
        dx = abs(point1.X - point2.X)
        dy = abs(point1.Y - point2.Y)
        dxy = math.sqrt(dx ** 2 + dy ** 2)
        alpha = math.degrees(math.atan2(dxy, dz))
        if alpha < vertical_tolerance:
            # print('vertical: ', alpha)
            return 'vertical'
        elif alpha < weird_thr_upper:
            # print('weird: ', alpha)
            return 'weird'
        elif alpha < sloped_thr_upper:
            # print('sloped: ', alpha)
            return 'sloped'
    else:
        # print('horizontal: ', 90)
        return 'horizontal'
    

export = SlopedPipesCollector()

