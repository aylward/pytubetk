import itk


def get_children_as_list(
    grp: itk.GroupSpatialObject, child_type: str = "Tube"
) -> list:
    soList = grp.GetChildren(grp.GetMaximumDepth(), child_type)
    return [itk.down_cast(soList[i]) for i in range(len(soList))]


def read_group(filename: str, Dimension: int = 3) -> itk.GroupSpatialObject:
    TubeFileReaderType = itk.SpatialObjectReader[Dimension]

    tubeFileReader = TubeFileReaderType.New()
    tubeFileReader.SetFileName(filename)
    tubeFileReader.Update()

    return tubeFileReader.GetGroup()
