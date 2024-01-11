""" tube_viewer.py
This file contains the implementation of the tube_viewer class.

Classes:
    tube_viewer: A class for visualizing tubes.
"""
from tkinter import filedialog

import itk
from itk import TubeTK as ttk

from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkCellPicker,
    vtkPolyDataMapper,
    vtkRenderer,
    vtkRenderWindow,
    vtkRenderWindowInteractor,
)

from tube_utils import (
    get_children_as_list,
    get_tube_index_in_list,
    write_group
)
from tube_visualization_utils import (
    convert_tubes_to_polylines,
    convert_tubes_to_surfaces
)


class tube_viewer:
    def __init__(self, tubes):
        """
        The constructor for the tube_viewer class.
        """
        self.tubes = tubes

        self.tube_list = get_children_as_list(tubes)
        self.num_tubes = len(self.tube_list)

        self.tube_polylines = convert_tubes_to_polylines(tubes)
        self.tube_surfaces = convert_tubes_to_surfaces(tubes)

        self.data_image = None

        self.selected_tubes_ids = []
        self.selected_tubes_points = []
        self.selected_tubes_actors = []
        self.multiple_selections_enabled = False

        self.renderWindowInteractor = None

    def set_image(self, data_image):
        """
        Sets the optional image to be used with the tube visualizations.

        Args:
            data_image (itk.Image[itk.F, 3]): The image to be used.

        Returns:
            None
        """
        self.data_image = data_image

        tubeImageConv = ttk.ConvertTubesToImage[itk.Image[itk.F, 3]].New()
        tubeImageConv.SetInput(self.tubes)
        tubeImageConv.SetTemplateImage(data_image)
        tubeImageConv.SetColorByPointId(True)
        tubeImageConv.SetUseRadius(True)
        tubeImageConv.Update()
        self.tube_image = tubeImageConv.GetOutput()

        self.selected_tubes_ids = []
        self.selected_tubes_points = []
        self.selected_tubes_actors = []

    def _getSelectedTubesAsList(self):
        """
        Private function to get the selected tubes as a list.
        """
        selected_tubes_list = []
        for i in range(len(self.tube_list)):
            id = self.tube_list[i].GetId()
            if id in self.selected_tubes_ids:
                selected_tubes_list.append(self.tube_list[i])
        return selected_tubes_list

    def _updateCurrentTubeActor(self, pickedPos, actor, renwin):
        """
        Private function to updated the viz of currently selected tube.
        """
        if len(self.selected_tubes_actors) > 0:
            if (
                self.multiple_selections_enabled is False and
                not ([actor] == self.selected_tubes_actors)
            ):
                for tube_actor in self.selected_tubes_actors:
                    tube_actor.GetMapper().ScalarVisibilityOn()
                    tube_actor.GetMapper().Update()
                    tube_actor.Modified()
                self.selected_tubes_ids = []
                self.selected_tubes_points = []
                self.selected_tubes_actors = []
            elif (
                self.multiple_selections_enabled is True and
                actor in self.selected_tubes_actors
            ):
                actor.GetMapper().ScalarVisibilityOn()
                actor.GetMapper().Update()
                actor.Modified()
                idx = self.selected_tubes_actors.index(actor)
                self.selected_tubes_actors = \
                    self.selected_tubes_actors[0:idx] + \
                    self.selected_tubes_actors[idx:-1]
                self.selected_tubes_ids = \
                    self.selected_tubes_ids[0:idx] + \
                    self.selected_tubes_ids[idx:-1]
                self.selected_tubes_points = \
                    self.selected_tubes_points[0:idx] + \
                    self.selected_tubes_points[idx:-1]
                actor = None
        if actor is not None:
            pos = [pickedPos[0], pickedPos[1], pickedPos[2]]
            tube_poly_data = actor.GetMapper().GetInput()
            tube_id = tube_poly_data.GetPointData().GetScalars(
                "Id"
            ).GetTuple(0)[0]
            tube = self.tube_list[
                get_tube_index_in_list(tube_id, self.tube_list)
                ]
            tube_length = tube.GetNumberOfPoints()
            point = tube.ClosestPointInWorldSpace(pos)
            point_id = point.GetId()
            point_pos = point.GetPositionInWorldSpace()
            point_radius = point.GetRadiusInWorldSpace()
            if actor not in self.selected_tubes_actors:
                self.selected_tubes_ids.append(tube_id)
                self.selected_tubes_points.append(point_id)
                self.selected_tubes_actors.append(actor)
                actor.GetMapper().ScalarVisibilityOff()
                actor.GetProperty().SetColor(1, 1, 1)
                actor.GetMapper().Update()
                actor.Modified()
                self.selected_tubes_actors.append(actor)
            print("Selected position: ", pos)
            print("  Tube id: ", tube_id)
            print("  Tube Length: ", tube_length)
            print("    Point id: ", point_id)
            print("    Point position: ", point_pos)
            print("    Point radius: ", point_radius)
            print("", flush=True)
            print("", flush=True)
        renwin.Render()

    def _leftButtonPressEvent(self, obj, event):
        """
        Private function to handle left button press events.
        """
        clickPos = obj.GetEventPosition()

        picker = vtkCellPicker()
        picker.SetTolerance(0.0005)
        picker.Pick(
            clickPos[0],
            clickPos[1],
            0,
            self.renderWindowInteractor.GetRenderWindow()
                .GetRenderers().GetFirstRenderer(),
        )
        pickedActor = picker.GetActor()
        pickedPos = picker.GetPickPosition()

        self.multiple_selections_enabled = bool(obj.GetShiftKey())
        if pickedActor is not None:
            self._updateCurrentTubeActor(
                pickedPos, pickedActor, obj.GetRenderWindow()
            )

        return 0

    def _keyPressEvent(self, obj, event):
        """
        Private function to handle key press events.
        """
        key = self.renderWindowInteractor.GetKeySym()

        if key == "Escape":
            self.renderWindowInteractor.GetRenderWindow().Finalize()
            self.renderWindowInteractor.TerminateApp()
        elif key == "w":
            filename = filedialog.asksaveasfilename(
                initialfile="selected_tubes.tre",
                defaultextension=".tre",
                filetypes=[("tre files", "*.tre")],
                initialdir="."
            )
            if filename != "":
                tubes_list = self._getSelectedTubesAsList()
                tubes_group = itk.GroupSpatialObject[3].New()
                for i in range(len(tubes_list)):
                    tubes_group.AddChild(tubes_list[i])
                write_group(tubes_group, filename)
        elif key == "W":
            filename = filedialog.asksaveasfilename(
                initialfile="tubes.tre",
                defaultextension=".tre",
                filetypes=[("tre files", "*.tre")],
                initialdir="."
            )
            if filename != "":
                tubes_group = itk.GroupSpatialObject[3].New()
                for i in range(len(self.tube_list)):
                    tubes_group.AddChild(self.tube_list[i])
                write_group(tubes_group, filename)
        return 0

    def _render(self, pdata, param="Radius", vessel_list=[]):
        """
        Private function to render the tubes.
        """
        renderer = vtkRenderer()

        renderWindow = vtkRenderWindow()
        renderWindow.SetWindowName(param)
        renderWindow.AddRenderer(renderer)

        self.renderWindowInteractor = vtkRenderWindowInteractor()
        self.renderWindowInteractor.SetRenderWindow(renderWindow)

        self.renderWindowInteractor.SetInteractorStyle(
            vtkInteractorStyleTrackballCamera()
        )

        self.renderWindowInteractor.AddObserver(
            "LeftButtonPressEvent", self._leftButtonPressEvent
        )
        self.renderWindowInteractor.AddObserver(
            "KeyPressEvent", self._keyPressEvent
        )

        mapper = []
        actor = []
        for i in range(self.num_tubes):
            if vessel_list == [] or i in vessel_list:
                pdata[i].GetPointData().SetActiveScalars(param)

                mapper.append(vtkPolyDataMapper())
                mapper[-1].SetInputData(pdata[i])
                mapper[-1].ScalarVisibilityOn()

                actor.append(vtkActor())
                actor[-1].SetMapper(mapper[-1])

                renderer.AddActor(actor[-1])

        renderWindow.Render()
        self.renderWindowInteractor.Initialize()
        self.renderWindowInteractor.Start()

    def render_tubes_as_polylines(self, param="Radius", vessel_list=[]):
        """
        Renders the tubes' centerlines as polylines.

        Args:
            param (str, optional): The parameter to be used for coloring tubes.
                Defaults to "Radius".
            vessel_list (list, optional): The list of tubes to be rendered.
                Defaults to []. If empty, all tubes are rendered.

        Returns:
            None
        """
        if self.tube_polylines == []:
            self.tube_polylines = convert_tubes_to_polylines(self.tubes)
        self._render(self.tube_polylines, param, vessel_list)

    def render_tubes_as_surfaces(self, param="Radius", vessel_list=[]):
        """
        Renders the tubes as surfaces.

        Args:
            param (str, optional): The parameter to be used for coloring tubes.
                Defaults to "Radius".
            vessel_list (list, optional): The list of tubes to be rendered.
                Defaults to []. If empty, all tubes are rendered.

        Returns:
            None
        """
        if self.tube_surfaces == []:
            self.tube_surfaces = convert_tubes_to_surfaces(self.tubes)
        self._render(self.tube_surfaces, param, vessel_list)
