from functools import cache

import itk
import vtk
from itk import TubeTK as ttk
from tube_utils import *
from vtkmodules.vtkCommonCore import vtkDoubleArray, vtkPoints
from vtkmodules.vtkCommonDataModel import (
    vtkCellArray,
    vtkPointData,
    vtkPolyData,
    vtkPolyLine,
)
from vtkmodules.vtkFiltersCore import vtkTubeFilter
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkCellPicker,
    vtkPolyDataMapper,
    vtkRenderer,
    vtkRenderWindow,
    vtkRenderWindowInteractor,
)


@cache
def convert_tubes_to_polylines(tubes):
    dimension = 3

    tube_polylines = []

    tubes.Update()
    tube_list = get_children_as_list(tubes)
    num_tubes = len(tube_list)

    for tube in tube_list:
        tube.Update()
        tube.RemoveDuplicatePointsInObjectSpace()
        tube.ComputeTangentsAndNormals()

        tube_num_points = tube.GetNumberOfPoints()

        data_point = vtkPoints()
        data_point.SetNumberOfPoints(tube_num_points)

        data_radius = vtkDoubleArray()
        data_radius.SetName("Radius")
        data_radius.SetNumberOfTuples(tube_num_points)

        data_id = vtkDoubleArray()
        data_id.SetName("Id")
        data_id.SetNumberOfTuples(tube_num_points)

        data_color = vtkDoubleArray()
        data_color.SetName("Color")
        data_color.SetNumberOfComponents(4)
        data_color.SetNumberOfTuples(tube_num_points)

        data_t = vtkDoubleArray()
        data_t.SetName("Tangent")
        data_t.SetNumberOfComponents(dimension)
        data_t.SetNumberOfTuples(tube_num_points)

        data_n1 = vtkDoubleArray()
        data_n1.SetName("Normal1")
        data_n1.SetNumberOfComponents(dimension)
        data_n1.SetNumberOfTuples(tube_num_points)

        data_n2 = vtkDoubleArray()
        data_n2.SetName("Normal2")
        data_n2.SetNumberOfComponents(dimension)
        data_n2.SetNumberOfTuples(tube_num_points)

        data_a1 = vtkDoubleArray()
        data_a1.SetName("Alpha1")
        data_a1.SetNumberOfTuples(tube_num_points)

        data_a2 = vtkDoubleArray()
        data_a2.SetName("Alpha2")
        data_a2.SetNumberOfTuples(tube_num_points)

        data_a3 = vtkDoubleArray()
        data_a3.SetName("Alpha3")
        data_a3.SetNumberOfTuples(tube_num_points)

        data_ridgeness = vtkDoubleArray()
        data_ridgeness.SetName("Ridgeness")
        data_ridgeness.SetNumberOfTuples(tube_num_points)

        data_medialness = vtkDoubleArray()
        data_medialness.SetName("Medialness")
        data_medialness.SetNumberOfTuples(tube_num_points)

        data_branchness = vtkDoubleArray()
        data_branchness.SetName("Branchness")
        data_branchness.SetNumberOfTuples(tube_num_points)

        data_intensity = vtkDoubleArray()
        data_intensity.SetName("Intensity")
        data_intensity.SetNumberOfTuples(tube_num_points)

        data_curvature = vtkDoubleArray()
        data_curvature.SetName("Curvature")
        data_curvature.SetNumberOfTuples(tube_num_points)

        data_roundness = vtkDoubleArray()
        data_roundness.SetName("Roundness")
        data_roundness.SetNumberOfTuples(tube_num_points)

        data_levelness = vtkDoubleArray()
        data_levelness.SetName("Levelness")
        data_levelness.SetNumberOfTuples(tube_num_points)

        tube_line = vtkPolyLine()
        tube_line.GetPointIds().SetNumberOfIds(tube_num_points)
        for point_num, point in enumerate(tube.GetPoints()):
            tube_line.GetPointIds().SetId(point_num, point_num)

            data_id.SetTuple1(point_num, tube.GetId())
            data_point.SetPoint(point_num, *point.GetPositionInWorldSpace())
            data_radius.SetTuple1(point_num, point.GetRadiusInWorldSpace())
            data_color.SetTuple4(point_num, *point.GetColor())
            data_t.SetTuple3(point_num, *point.GetTangentInWorldSpace())
            data_n1.SetTuple3(point_num, *point.GetNormal1InWorldSpace())
            data_n2.SetTuple3(point_num, *point.GetNormal2InWorldSpace())

            data_ridgeness.SetTuple1(point_num, point.GetRidgeness())
            data_medialness.SetTuple1(point_num, point.GetMedialness())
            data_branchness.SetTuple1(point_num, point.GetBranchness())
            data_curvature.SetTuple1(point_num, point.GetCurvature())
            data_intensity.SetTuple1(point_num, point.GetIntensity())
            data_roundness.SetTuple1(point_num, point.GetRoundness())
            data_levelness.SetTuple1(point_num, point.GetLevelness())
            data_a1.SetTuple1(point_num, point.GetAlpha1())
            data_a2.SetTuple1(point_num, point.GetAlpha2())
            data_a3.SetTuple1(point_num, point.GetAlpha3())

        tube_line_array = vtkCellArray()
        tube_line_array.InsertNextCell(tube_line)

        tube_polylines.append(vtkPolyData())
        tube_polylines[-1].SetPoints(data_point)
        tube_polylines[-1].SetLines(tube_line_array)
        tube_polylines[-1].GetPointData().AddArray(data_radius)
        tube_polylines[-1].GetPointData().AddArray(data_id)
        tube_polylines[-1].GetPointData().AddArray(data_color)
        tube_polylines[-1].GetPointData().AddArray(data_t)
        tube_polylines[-1].GetPointData().AddArray(data_n1)
        tube_polylines[-1].GetPointData().AddArray(data_n2)
        tube_polylines[-1].GetPointData().AddArray(data_ridgeness)
        tube_polylines[-1].GetPointData().AddArray(data_medialness)
        tube_polylines[-1].GetPointData().AddArray(data_branchness)
        tube_polylines[-1].GetPointData().AddArray(data_curvature)
        tube_polylines[-1].GetPointData().AddArray(data_intensity)
        tube_polylines[-1].GetPointData().AddArray(data_roundness)
        tube_polylines[-1].GetPointData().AddArray(data_levelness)
        tube_polylines[-1].GetPointData().AddArray(data_a1)
        tube_polylines[-1].GetPointData().AddArray(data_a2)
        tube_polylines[-1].GetPointData().AddArray(data_a3)
        tube_polylines[-1].GetPointData().SetActiveScalars("Radius")

    return tube_polylines


@cache
def convert_tubes_to_surfaces(tubes, number_of_sides=5):
    tubes.Update()
    tube_list = get_children_as_list(tubes)
    num_tubes = len(tube_list)

    tube_polylines = convert_tubes_to_polylines(tubes)

    tube_surfaces = []
    for i in range(num_tubes):
        tFilter = vtkTubeFilter()
        tFilter.SetVaryRadiusToVaryRadiusByAbsoluteScalar()
        tFilter.CappingOn()
        tFilter.SetNumberOfSides(number_of_sides)
        tFilter.SetInputData(tube_polylines[i])
        tFilter.Update()
        tube_surfaces.append(tFilter.GetOutput())

    return tube_surfaces
