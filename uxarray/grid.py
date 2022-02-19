"""uxarray grid module."""
import math
import xarray as xr
import numpy as np
from ast import Raise
from logging import raiseExceptions

from pathlib import PurePath
import os


class Grid:
    """A class for uxarray grid object.

    Examples
    ========
    import uxarray as ux
    # open an exodus file with Grid object
    mesh = ux.Grid("filename.g")

    # save as ugrid file
    mesh.saveas("outfile.ug")
    """

    # Import read/write methods from files in this folder
    from ._exodus import read_exodus, write_exodus
    from ._ugrid import read_ugrid, write_ugrid
    from ._shpfile import read_shpfile
    from ._scrip import read_scrip

    def __init__(self, *args, **kwargs):
        """Initialize grid variables, decide if loading happens via file, verts
        or gridspec If loading from file, initialization happens via the
        specified file.
        Args: input file name with extension as a string
              vertex coordinates that form one face.
        kwargs: can be a dict initializing specific variables: kwargs = {"concave" : True, "islatlon" : True"}

        Raises:
            RuntimeError: File not found
        """
        # initialize possible variables
        for key, value in kwargs.items():
            if key == "latlon":
                self.islatlon = value
            elif key == "gridspec":
                self.gridspec = value

        self.filepath = None
        self.gridspec = None
        self.vertices = None
        self.islatlon = None
        self.concave = None
        self.meshFileType = None

        # this xarray variable holds an existing external netcdf file with loaded with xarray
        self.ext_ds = None

        # internal uxarray representation of mesh stored in internal object in_ds
        self.in_ds = xr.Dataset()

        # determine initialization type - string signifies a file, numpy array signifies a list of verts
        in_type = type(args[0])

        # check if this is a valid file:
        try:
            if os.path.isfile(args[0]) is False and in_type is not np.ndarray:
                print("File not found: ", args[0])
                exit()
            elif in_type is np.ndarray:
                self.vertices = args[0]
                self.from_vert()
        except ValueError as e:
            # initialize from vertices
            if in_type is np.ndarray:
                self.vertices = args[0]
                self.from_vert()

        # initialize from file
        if in_type is str and os.path.isfile(args[0]):
            self.filepath = args[0]
            self.from_file()

        # initialize for gridspec
        elif in_type is str:
            self.gridspec = args[0]
            self.from_gridspec()

        else:
            # this may just be initialization for options other than above
            pass

    # vertices init
    def from_vert(self):
        """Create a grid with one face with vertices specified by the given
        argument."""
        print("Initializing with vertices")
        self._init_mesh2()
        self.in_ds.Mesh2.attrs['topology_dimension'] = self.vertices[0].size

        self.in_ds["Mesh2"].topology_dimension

        x_coord = self.vertices.transpose()[0]
        y_coord = self.vertices.transpose()[1]

        # single face with all nodes
        num_nodes = x_coord.size
        conn = list(range(0, num_nodes))
        conn = [conn]

        self.in_ds["Mesh2_node_x"] = xr.DataArray(data=xr.DataArray(x_coord),
                                                  dims=["nMesh2_node"])
        self.in_ds["Mesh2_node_y"] = xr.DataArray(data=xr.DataArray(y_coord),
                                                  dims=["nMesh2_node"])
        self.in_ds["Mesh2_face_nodes"] = xr.DataArray(
            data=xr.DataArray(conn),
            dims=["nMesh2_face", "nMaxMesh2_face_nodes"],
            attrs={
                "cf_role": "face_node_connectivity",
                "_FillValue": -1,
                "start_index": 0
            })

    # TODO: gridspec init
    def from_gridspec(self):
        print("initializing with gridspec")

    # load mesh from a file
    def from_file(self):
        """Loads a mesh file Also, called by __init__ routine This routine will
        automatically detect if it is a UGrid, SCRIP, Exodus, or shape file.

        Raises:
            RuntimeError: Invalid file type
        """
        # find the file type
        self.meshFileType = self.find_type()

        # call reader as per meshFileType
        if self.meshFileType == "exo":
            self.read_exodus(self.ext_ds)
        elif self.meshFileType == "scrip":
            self.read_scrip(self.ext_ds)
        elif self.meshFileType == "ugrid":
            self.read_ugrid(self.filepath)
        elif self.meshFileType == "shp":
            self.read_shpfile(self.filepath)
        else:
            raise RuntimeError("unknown file format.")

    # helper function to find file type
    def find_type(self):
        """Checks file path and contents to determine file type Also, called by
        __init__ routine This routine will automatically detect if it is a
        UGrid, SCRIP, Exodus, or shape file.

        Raises:
            RuntimeError: Invalid file type
        """

        try:
            # extract the file name and extension
            path = PurePath(self.filepath)
            file_extension = path.suffix

            # try to open file with xarray
            self.ext_ds = xr.open_dataset(self.filepath, mask_and_scale=False)
            #
        except (TypeError, AttributeError) as e:
            msg = str(e) + ': {}'.format(self.filepath)
            print(msg)
            raise RuntimeError(msg)
            exit
        except (RuntimeError, OSError) as e:
            # check if this is a shp file
            # we won't use xarray to load that file
            if file_extension == ".shp":
                self.meshFileType = "shp"
            else:
                msg = str(e) + ': {}'.format(self.filepath)
                print(msg)
                raise RuntimeError(msg)
                exit
        except ValueError as e:
            # check if this is a shp file
            # we won't use xarray to load that file
            if file_extension == ".shp":
                self.meshFileType = "shp"
            else:
                msg = str(e) + ': {}'.format(self.filepath)
                print(msg)
                raise RuntimeError(msg)
                exit

        # Detect mesh file type, based on attributes of ext_ds:
        # if ext_ds has coordx or coord - call it exo format
        # if ext_ds has grid_size - call it SCRIP format
        # if ext_ds has ? read as shape file populate_scrip_dataformat
        # TODO: add detection of shpfile etc.
        try:
            self.ext_ds.coordx
            self.meshFileType = "exo"
        except AttributeError as e:
            pass
        try:
            self.ext_ds.grid_center_lon
            self.meshFileType = "scrip"
        except AttributeError as e:
            pass
        try:
            self.ext_ds.coord
            self.meshFileType = "exo"
        except AttributeError as e:
            pass
        try:
            self.ext_ds.Mesh2
            self.meshFileType = "ugrid"
        except AttributeError as e:
            pass

        if self.meshFileType is None:
            print("mesh file not supported")

        # print(self.filepath, " is of type: ", self.meshFileType)
        return self.meshFileType

    # initialize mesh2 DataVariable for uxarray
    def _init_mesh2(self):
        # set default values and initialize Datavariable "Mesh2" for uxarray
        self.in_ds["Mesh2"] = xr.DataArray(
            data=0,
            attrs={
                "cf_role": "mesh_topology",
                "long_name": "Topology data of unstructured mesh",
                "topology_dimension": -1,
                "node_coordinates": "Mesh2_node_x Mesh2_node_y Mesh2_node_z",
                "node_dimension": "nMesh2_node",
                "face_node_connectivity": "Mesh2_face_nodes",
                "face_dimension": "nMesh2_face"
            })

    # renames the grid file
    def saveas_file(self, filename):
        path = PurePath(self.filepath)
        old_filename = path.name
        new_filepath = path.parent / filename
        self.filepath = str(new_filepath)
        self.write_ugrid(self.filepath)
        print(self.filepath)

    # Calculate the area of all faces.
    def calculate_total_face_area(self):
        pass

    # Build the node-face connectivity array.
    def build_node_face_connectivity(self):
        pass

    # Build the edge-face connectivity array.
    def build_edge_face_connectivity(self):
        pass

    # Build the array of latitude-longitude bounding boxes.
    def buildlatlon_bounds(self):
        pass

    # Validate that the grid conforms to the UXGrid standards.
    def validate(self):
        pass

    def write(self, outfile, format=""):
        if format == "":
            path = PurePath(outfile)
            format = path.suffix

        if format == ".ugrid" or format == ".ug":
            self.write_ugrid(outfile)
        elif format == ".g" or format == ".exo":
            self.write_exodus(outfile)
        else:
            print("Format not supported for writing. ", format)
