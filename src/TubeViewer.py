import sys

from tube_viewer import tube_viewer
from tube_utils import read_group

def main():
    args = sys.argv[1:]
    if len(args) == 1:
        grp = read_group(args[0])
        viewer2 = tube_viewer(tubes=vgrp_base)
        viewer2.render_tubes_as_surfaces(param="Radius")
    else:
        print("USAGE: tubeviewer <filename.tre>")
