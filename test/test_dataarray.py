import os

from unittest import TestCase
from pathlib import Path

import uxarray as ux

current_path = Path(os.path.dirname(os.path.realpath(__file__)))

gridfile_ne30 = current_path / "meshfiles" / "ugrid" / "outCSne30" / "outCSne30.ug"
dsfile_var2_ne30 = current_path / "meshfiles" / "ugrid" / "outCSne30" / "outCSne30_vortex.nc"

dsfiles_mf_ne30 = str(
    current_path) + "/meshfiles/ugrid/outCSne30/outCSne30_*.nc"

gridfile_geoflow = current_path / "meshfiles" / "ugrid" / "geoflow-small" / "grid.nc"
dsfile_v1_geoflow = current_path / "meshfiles" / "ugrid" / "geoflow-small" / "v1.nc"


class TestDataArrayGDF(TestCase):

    def test_construction_and_return(self):

        outCSne30_uxds = ux.open_dataset(gridfile_ne30, dsfile_var2_ne30)

        gdf = outCSne30_uxds['psi'].to_geodataframe()

        pass

    def test_mpl_poly_collection(self):
        outCSne30_uxds = ux.open_dataset(gridfile_ne30, dsfile_var2_ne30)
        poly_collection = outCSne30_uxds['psi'].to_polycollection()
        pass
