from tube_utils import *
from tube_visualization_utils import *


class tube_viewer:
    def __init__(self, tubes):
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

    def _updateCurrentTubeActor(self, pickedPos, actor, renwin):
        if len(self.selected_tubes_actors) > 0:
            if (self.multiple_selections_enabled == False and [actor] != self.selected_tubes_actors):
                for tube_actor in self.selected_tubes_actors:
                    tube_actor.GetMapper().ScalarVisibilityOn()
                    tube_actor.GetMapper().Update()
                    tube_actor.Modified()
                self.selected_tubes_ids = []
                self.selected_tubes_points = []
                self.selected_tubes_actors = []
            elif (self.multiple_selections_enabled == True and actor in self.selected_tubes_actors):
                actor.GetMapper().ScalarVisibilityOn()
                actor.GetMapper().Update()
                actor.Modified()
                idx = self.selected_tubes_actors.index(actor)
                self.selected_tubes_ids.remove(self.selected_tubes_ids[idx])
                self.selected_tubes_points.remove(self.selected_tubes_points[idx])
                self.selected_tubes_actors.remove(self.selected_tubes_actors[idx])
                actor = None
        if actor != None:
            pos = [pickedPos[0], pickedPos[1], pickedPos[2]]
            tube_poly_data = actor.GetMapper().GetInput()
            tube_id = tube_poly_data.GetPointData().GetScalars("Id").GetTuple(0)
            tube_length = tube_poly_data.GetNumberOfPoints()
            point_id = tube_poly_data.FindPoint(pos)
            point_pos = tube_poly_data.GetPoint(point_id)
            point_radius = tube_poly_data.GetPointData().GetScalars("Radius").GetTuple(point_id)[0]
            if not actor in self.selected_tubes_actors:
                self.selected_tubes_ids.append(tube_id)
                self.selected_tubes_points.append(point_id)
                self.selected_tubes_actors.append(actor)
                actor.GetMapper().ScalarVisibilityOff()
                actor.GetProperty().SetColor(1, 1, 1)
                actor.GetMapper().Update()
                actor.Modified()
            print("Selected position: ", pos)
            print("  Tube id: ", tube_id[0])
            print("  Tube Length: ", tube_length)
            print("    Point id: ", point_id)
            print("    Point position: ", point_pos)
            print("    Point radius: ", point_radius)
            print("", flush=True)
        renwin.Render()

    def _leftButtonPressEvent(self, obj, event):
        clickPos = obj.GetEventPosition()

        picker = vtkCellPicker()
        picker.SetTolerance(0.0005)
        picker.Pick(
            clickPos[0],
            clickPos[1],
            0,
            self.renderWindowInteractor.GetRenderWindow().GetRenderers().GetFirstRenderer(),
        )
        pickedActor = picker.GetActor()
        pickedPos = picker.GetPickPosition()

        self.multiple_selections_enabled = obj.GetShiftKey()
        if pickedActor != None:
            self._updateCurrentTubeActor(
                pickedPos, pickedActor, obj.GetRenderWindow()
            )

        return 0

    def _keyPressEvent(self, obj, event):
        key = self.renderWindowInteractor.GetKeySym()

        if key == "Escape":
            self.renderWindowInteractor.GetRenderWindow().Finalize()
            self.renderWindowInteractor.TerminateApp()

        return 0

    def _render(self, pdata, param="Radius", vessel_list=[]):
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

                #if self.selected_tubes != [] and i in self.selected_tubes:
                    #actor[-1].GetProperty().SetColor(1, 0, 0)
                    #mapper[-1].ScalarVisibilityOff()
                    #mapper[-1].Update()
                    #actor[-1].Modified()

        renderWindow.Render()
        self.renderWindowInteractor.Initialize()
        self.renderWindowInteractor.Start()

    def render_tubes_as_polylines(self, param="Radius", vessel_list=[]):
        if self.tube_polylines == []:
            self.tube_polylines = convert_tubes_to_polylines(self.tubes)
        self._render(self.tube_polylines, param, vessel_list)

    def render_tubes_as_surfaces(self, param="Radius", vessel_list=[]):
        if self.tube_surfaces == []:
            self.tube_surfaces = convert_tubes_to_surfaces(self.tubes)
        self._render(self.tube_surfaces, param, vessel_list)
