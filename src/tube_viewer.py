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
        self.tube_image = None

        self.selected_tubes = []
        self.current_tube_actor = None

    def set_image(self, data_image):
        self.data_image = data_image

        tubeImageConv = ttk.ConvertTubesToImage[itk.Image[itk.F, 3]].New()
        tubeImageConv.SetInput(self.tubes)
        tubeImageConv.SetTemplateImage(data_image)
        tubeImageConv.SetColorByPointId(True)
        tubeImageConv.SetUseRadius(True)
        tubeImageConv.Update()
        self.tube_image = tubeImageConv.GetOutput()

        self.selected_tubes = []
        self.current_tube_actor = None

    def select_tubes(self, tube_list):
        self.selected_tubes = tube_list

    def select_tubes_by_id(self, tube_id_list):
        self.selected_tubes = []
        for i, tube in enumerate(self.tubes):
            if tube.GetId() in tube_id_list:
                self.selected_tubes.append(i)

    def _updateCurrentTubeActor(self, pickedPos, actor, renwin):
        if self.current_tube_actor != actor:
            if self.current_tube_actor != None:
                self.current_tube_actor.GetMapper().ScalarVisibilityOn()
                self.current_tube_actor.GetMapper().Update()
                self.current_tube_actor.Modified()
            self.current_tube_actor = actor
            if self.current_tube_actor != None:
                self.current_tube_actor.GetMapper().ScalarVisibilityOff()
                self.current_tube_actor.GetMapper().Update()
                self.current_tube_actor.Modified()
            renwin.Render()
        pos = [pickedPos[0], pickedPos[1], pickedPos[2]]
        print("Selected position: ", pos, flush=True)
        if self.tube_image != None:
            indx = self.tube_image.TransformPhysicalPointToIndex(pos)
            id = self.tube_image.GetPixel(indx)
            if id == 0:
                print("ERROR: no tube selected", flush=True)
                return
            tube_id = int(id)
            print("          tube id: ", tube_id, flush=True)
            pnt_id = 0
            if id - int(id) != 0:
                pnt_id = int(1.0 / (id - int(id)) - 1)
            print("         point id: ", pnt_id, flush=True)
            tube_tube = None
            for tube in self.tube_list:
                if tube.GetId() == tube_id:
                    tube_tube = tube
                    break
            if tube_tube == None:
                print("ERROR: tube not found", flush=True)
                return
            print(
                "         position: ",
                tube_tube.GetPoint(pnt_id).GetPositionInWorldSpace(),
                flush=True,
            )
            print(
                "           radius: ",
                tube_tube.GetPoint(pnt_id).GetRadiusInWorldSpace(),
                flush=True,
            )

    def _leftButtonPressEvent(self, obj, event):
        clickPos = obj.GetEventPosition()

        picker = vtkCellPicker()
        picker.SetTolerance(0.0005)
        picker.Pick(
            clickPos[0],
            clickPos[1],
            0,
            obj.GetRenderWindow().GetRenderers().GetFirstRenderer(),
        )
        pickedActor = picker.GetActor()
        pickedPos = picker.GetPickPosition()

        if pickedActor != None:
            self._updateCurrentTubeActor(
                pickedPos, pickedActor, obj.GetRenderWindow()
            )

        return 0

    def _render(self, pdata, param="Radius", vessel_list=[]):
        renderer = vtkRenderer()

        renderWindow = vtkRenderWindow()
        renderWindow.SetWindowName(param)
        renderWindow.AddRenderer(renderer)

        renderWindowInteractor = vtkRenderWindowInteractor()
        renderWindowInteractor.SetRenderWindow(renderWindow)

        renderWindowInteractor.SetInteractorStyle(
            vtkInteractorStyleTrackballCamera()
        )
        # renderWindowInteractor.RemoveObservers("LeftButtonPressEvent")
        renderWindowInteractor.AddObserver(
            "LeftButtonPressEvent", self._leftButtonPressEvent
        )

        mapper = []
        actor = []
        for i in range(self.num_tubes):
            if vessel_list == [] or i in vessel_list:
                # pdata[i].GetPointData().SetActiveScalars(param)

                mapper.append(vtkPolyDataMapper())
                mapper[-1].SetInputData(pdata[i])
                mapper[-1].ScalarVisibilityOn()

                actor.append(vtkActor())
                actor[-1].SetMapper(mapper[-1])

                renderer.AddActor(actor[-1])

                if self.selected_tubes != [] and i in self.selected_tubes:
                    actor[-1].GetProperty().SetColor(1, 0, 0)
                    mapper[-1].ScalarVisibilityOff()
                    mapper[-1].Update()
                    actor[-1].Modified()

        renderWindow.Render()
        renderWindowInteractor.Initialize()
        renderWindowInteractor.Start()

    def render_tubes_as_polylines(self, param="Radius", vessel_list=[]):
        if self.tube_polylines == []:
            self.tube_polylines = convert_tubes_to_polylines(self.tubes)
        self._render(self.tube_polylines, param, vessel_list)

    def render_tubes_as_surfaces(self, param="Radius", vessel_list=[]):
        if self.tube_surfaces == []:
            self.tube_surfaces = convert_tubes_to_surfaces(self.tubes)

        self._render(self.tube_surfaces, param, vessel_list)
